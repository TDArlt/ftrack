# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import logging
import threading
import sys
import argparse
import json
import uuid

import ftrack_api

from ftrack_action_handler.action import BaseAction


##############################################################################
#                                                                            #
#           Custom utility methods (might not need to be changed)            #
#                                                                            #
##############################################################################

def getRealEntityFromTypedContext(session, entity):
    '''
    This one will return you a real entity behind a TypedContext-entity
    
    *session* is a `ftrack_api.Session` instance

    *entity* should be a tuple containing the entity type of `TypedContext`
    and (more important) the entity id.
    '''
    return session.get('TypedContext', entity['id'])

def async(fn):
    '''Run *fn* asynchronously.'''
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
    return wrapper

def get_filter_string(entity_ids):
    '''Return a comma separated string of quoted ids from *entity_ids* list.'''
    return ', '.join(
        '"{0}"'.format(entity_id) for entity_id in entity_ids
    )

class MainAction(BaseAction):
    '''This is an bare bone action'''

    ##############################################################################
    #                                                                            #
    #                           Space for custom methods                         #
    #                                                                            #
    ##############################################################################



    @async
    def mainAsyncAction(self, selection, user_id=None):
        session = ftrack_api.Session(
            auto_connect_event_hub=False
        )
        job = session.create('Job', {
            'user_id': user_id,
            'status': 'running',
            'data': json.dumps({
                'description': 'Finding real entities'
            })
        })
        session.commit()

        try:
            # Do, whatever you like
            #ftrack-python-api.rtd.ftrack.com/en/latest/example/job.html
            realEntities = []

            for entity in selection:
                searchType = 'TypedContext'
                if (entity['entityType'] == 'task'):
                    searchType = 'Task'

                realEntities.append(session.get(searchType, entity['entityId']))

            html = "\
                    <html>\
                        <body>\
                        <h3>You selected:</h3>\
                            {0}\
                        </body>\
                    </html>" .format(realEntities)

            # have a html file to attach to job list
            filename = "/example-{0}.html".format(str(uuid.uuid1()))
            
            server_location = session.query('Location where name is "ftrack.server"').one()
            #f=open(filename,"w")
            #f.write(html)
            #f.close()
            component = session.create_component(
                filename,
                data={'name': 'My file'},
                location='auto'
            )
            session.commit()
            #session.create(
            #    'JobComponent',
            #    {'component_id': component['id'], 'job_id': job['id']}
            #)


            job['status'] = 'done'
            session.commit()

        except BaseException as exc:
            self.logger.exception('Async action failed')
            session.rollback()
            job['status'] = 'failed'
            job['data'] = json.dumps({
                'description': exc.message
            })
            session.commit()

            















    ##############################################################################
    #                                                                            #
    #                        Main parameters to be changed                       #
    #                                                                            #
    ##############################################################################

    #: Action identifier.
    identifier = 'de.unexpected.ftrack.testaction'

    #: Action label.
    label = 'unexpected Test'

    #: Action description
    description = 'A test case for ftrack Action'

    #: Icon for this one
    icon = 'https://mediathek.unexpected.de/img/applogo.png'

    #: The types of entities you like to support here
    SUPPORTED_ENTITY_TYPES = (
        'task' #'project', 'component', 'task'
    )

    def discover(self, session, entities, event):
        '''Checks the selected entities and/or events and sessions.
        Return True, if you like to show the interaction icon and False, if you do not like the selection

        *session* is a `ftrack_api.Session` instance


        *entities* is a list of tuples each containing the entity type and the entity id.
        If the entity is a hierarchical you will always get the entity
        type TypedContext, once retrieved through a get operation you
        will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.

        *event* the unmodified original event
        '''

        # TODO: Write your custom method to define if this one is discoverable or not
        # Probably, you like to use getRealEntityFromTypedContext() to find out about
        # which entities you got here

        # Get selection
        selection = data = event['data']['selection']
        
        # Sample method: There needs to be at least one selected and bust be within the supported types
        if (len(selection) >= 1):
            isValid = True

            for sel in selection:
                if (sel['entityType'].lower() not in self.SUPPORTED_ENTITY_TYPES):
                    isValid = False
            
            return isValid
        else:
            self.logger.info('No element selected!')
            return False


    def launch(self, session, entities, event):
        '''Callback method for the custom action.

        return either a bool ( True if successful or False if the action failed )
        or a dictionary with they keys `message` and `success`, the message should be a
        string and will be displayed as feedback to the user, success should be a bool,
        True if successful or False if the action failed.

        *session* is a `ftrack_api.Session` instance

        *entities* is a list of tuples each containing the entity type and the entity id.
        If the entity is a hierarchical you will always get the entity
        type TypedContext, once retrieved through a get operation you
        will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.

        *event* the unmodified original event

        '''

        self.logger.info(
            u'Launching action with selection {0}'.format(entities)
        )

        data = event['data']
        logging.info(u'Launching action with data: {0}'.format(data))

        # TODO: Write your custom method for your action
        # Probably, you like to use getRealEntityFromTypedContext() to find out about
        # which entities you got here

        # Sample: Run async method
        self.mainAsyncAction(data['selection'], event['source']['user']['id'])


        return {
            'success': True,
            'message': 'Started operation for {0} selected objects.'.format(len(data['selection']))
        }


    ##############################################################################
    #                                                                            #
    # You do not need to edit something below, as these are just utility methods #
    #                      for discovery and registration                        #
    #                                                                            #
    ##############################################################################




    def _discover(self, event):
        '''Returns the parameters to show the interaction icon in the Actions Panel'''
        args = self._translate_event(
            self.session, event
        )

        accepts = self.discover(
            self.session, *args
        )

        if accepts:
            return {
                'items': [{
                    'label': self.label,
                    'variant': self.variant,
                    'description': self.description,
                    'actionIdentifier': self.identifier,
                    'icon': self.icon,
                }]
            }


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''
    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(session, ftrack_api.session.Session):
        return

    action_handler = MainAction(session)
    action_handler.register()


def main(arguments=None):
    '''Set up logging and register action.'''
    if arguments is None:
        arguments = []

    parser = argparse.ArgumentParser()
    # Allow setting of logging level from arguments.
    loggingLevels = {}
    for level in (
        logging.NOTSET, logging.DEBUG, logging.INFO, logging.WARNING,
        logging.ERROR, logging.CRITICAL
    ):
        loggingLevels[logging.getLevelName(level).lower()] = level

    parser.add_argument(
        '-v', '--verbosity',
        help='Set the logging output verbosity.',
        choices=loggingLevels.keys(),
        default='info'
    )
    namespace = parser.parse_args(arguments)

    # Set up basic logging.
    logging.basicConfig(level=loggingLevels[namespace.verbosity])

    session = ftrack_api.Session()
    register(session)

    # Wait for events.
    logging.info(
        'Registered actions and listening for events. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))

