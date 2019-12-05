# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import logging
import threading
import sys
import argparse
import json
import tempfile
import os
import datetime
import calendar
from types import NoneType

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
    return session.get(entity[0], entity[1])

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

def extract_start_date(taskObject):
    try:
        if (not(type(taskObject['start_date']) is NoneType)):
            return datetime.datetime(
                taskObject['start_date'].year,
                taskObject['start_date'].month,
                taskObject['start_date'].day,
                taskObject['start_date'].hour,
                taskObject['start_date'].minute)
        else:
            return datetime.datetime(2000, 1, 1)
    except:
        return datetime.datetime(2000, 1, 1)

def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)):
        yield start_date + datetime.timedelta(n)


class unexCreateGanttChartAction(BaseAction):
    '''This is the action for creating a Gantt Chart'''
    
    ##############################################################################
    #                                                                            #
    #                        Main parameters to be changed                       #
    #                                                                            #
    ##############################################################################

    #: Action identifier.
    identifier = 'de.unexpected.ftrack.export.ganttchart'

    #: Action label.
    label = 'Export Gantt Chart'

    #: Action description
    description = 'Exports a Gantt Chart for the selected entities or project'

    #: Icon for this one
    #: Basis for this icon made by Freepik from www.flaticon.com
    icon = 'https://mediathek.unexpected.de/img/ftrack/gantt.png'

    #: The types of entities you like to support here
    SUPPORTED_ENTITY_TYPES = (
        'Project', 'Component', 'Task', 'TypedContext'
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
        
        # Sample method: There needs to be at least one selected and bust be within the supported types
        if (len(entities) >= 1):
            isValid = True

            for entity in entities:
                if (entity[0] not in self.SUPPORTED_ENTITY_TYPES):
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

        # Run exporter
        self.mainAsyncAction(entities, event['source']['user']['id'])


        return {
            'success': True,
            'message': 'Export started...'
        }


    ##############################################################################
    #                                                                            #
    #                           Space for custom methods                         #
    #                                                                            #
    ##############################################################################



    @async
    def mainAsyncAction(self, entities, user_id=None):
        '''
        The main action this one is doing inside a job
        '''
        
        # Setup a session for the running job
        session = ftrack_api.Session(
            auto_connect_event_hub=False
        )
        job = session.create('Job', {
            'user_id': user_id,
            'status': 'running',
            'data': json.dumps({
                'description': 'Exporting Gantt Chart...'
            })
        })
        session.commit()

        try:
            # TODO: Selection form before starting job:
            #  - Select, if we like to show assignee and status as well (which might not be a good idea for clients)
            #  - Select the scaling width (to create a scrollable page)

            # TODO: What about additional information (assignee, status)?
            # TODO: What about scaling of the chart? => Might just be a css-property on "main"-div (but we need to scale the marks as well!)
            # TODO: What about connections between tasks? => Show arrows?
            # TODO: What about hierarchy (sort and show parent-grouping?)


    
            realEntities = []
            printString = ""

            for entity in entities:
                oneObject = getRealEntityFromTypedContext(session, entity)

                # Handling projects: We will need to get all the tasks of the project
                if type(oneObject).__name__ == "Project":
                    tasks = session.query('select id from Task where project.name is "' + oneObject['name'] + '"')
                    realEntities.extend(tasks)
                    milestones = session.query('select id from Milestone where project.name is "' + oneObject['name'] + '"')
                    realEntities.extend(milestones)
                else:
                    realEntities.append(oneObject)
            
            realEntities = sorted(realEntities, key=extract_start_date)

            # Get min and max dates
            minDate = datetime.datetime(3000, 1, 1)
            maxDate = datetime.datetime(2000, 1, 1)
            for task in realEntities:
                if (task['start_date'] != None):
                    tStartDate = datetime.datetime(task['start_date'].year, task['start_date'].month, task['start_date'].day, task['start_date'].hour, task['start_date'].minute)
                    if (tStartDate < minDate):
                        minDate = tStartDate
                if (task['end_date'] != None):
                    tEndDate = datetime.datetime(task['end_date'].year, task['end_date'].month, task['end_date'].day, task['end_date'].hour, task['end_date'].minute)
                    if (tEndDate > maxDate):
                        maxDate = tEndDate
            daycount = (maxDate - minDate).days




            # Generate HTML file

            # CSS
            cssStyle = '''
            body {
                font-family: 'Roboto', sans-serif;
                padding: 0pt;
                margin: 0pt;
            }

            .main {
                position: relative;
                margin: 5pt;
                padding: 30pt 0% 20pt 0%;
                background-color: #ddd;
                border-radius: 2pt;
                z-index: -20;
            }

            .weekend_mark {
                position: absolute;
                top: 0%;
                margin: 0%;
                padding: 0%;
                background-color: #ccc;
                height: 100%;
                z-index: -10;
                box-sizing: border-box;
            }
            .week_mark, .month_mark {
                position: absolute;
                top: 0%;
                margin: 0%;
                padding: 0%;
                padding-left: 4pt;
                height: 10pt;
                border-left: 1pt #888 solid;
                height: 100%;
                font-size: 9pt;
                font-weight: bold;
                box-sizing: border-box;
            }

            .task {
                margin: 0pt 0pt 2pt 0pt;
                padding: 5pt;
                height: 38pt;
                position: relative;
                border: 1pt solid #000;
                border-radius: 2pt;
                box-sizing: border-box;
            }

            .task .name {
                font-size: 9pt;
                font-weight: bold;
            }

            .task .start {
                position: absolute;
                left: 5pt;
                bottom: 0pt;
                height: 10pt;
                font-size: 7pt;
            }
            .task .end {
                position: absolute;
                right: 5pt;
                bottom: 0pt;
                height: 10pt;
                font-size: 7pt;
            }

            .task .type {
                font-size: 7pt;
            }

            .milestone {
                margin: 0pt 0pt 2pt 0pt;
                padding: 5pt;
                height: 28pt;
                position: relative;
                border-left: solid 2pt #f00;
                box-sizing: border-box;
            }

            .milestone .caption {
                font-size: 9pt;
                font-weight: bold;
            }
            .milestone .end {
                position: absolute;
                left: 5pt;
                bottom: 0pt;
                height: 10pt;
                font-size: 7pt;
            }

            
            .milestone_bar {
                position: absolute;
                width: 2pt;
                background-color: #f00;
                top: 10pt;
                bottom: 0pt;
            }


            '''

            # General beginning

            filecontent = '''
            <html>
                <head>
                    <title>Gantt Chart</title>
                    <link href="https://fonts.googleapis.com/css?family=Roboto&display=swap" rel="stylesheet"> 
                    <style>''' + cssStyle + '''</style>
                </head>
                <body>
                <div class="main">
                    <div id="marks">
            '''

            # Write markers for weeks & months
            for single_date in daterange(minDate, maxDate):
                tLeft = ((single_date - minDate).days / float(daycount)) * 100.0

                if (single_date.weekday() == 5):
                    tLength = (2.0 / float(daycount)) * 100.0
                    filecontent += '''
                        <div class="weekend_mark" style="left: ''' + str(tLeft) + '''%; width: ''' + str(tLength) + '''%;"></div>
                    '''
                # if we have less than two months in our overview, mark each week beginning
                if (daycount < 60 and single_date.weekday() == 0):
                    tLength = (7.0 / float(daycount)) * 100.0
                    filecontent += '''
                        <div class="week_mark" style="left: ''' + str(tLeft) + '''%; width: ''' + str(tLength) + '''%;">
                            <div class="caption">''' + single_date.strftime("%m/%d") + '''</div>
                        </div>
                    '''
                elif (daycount > 60 and single_date.day == 1):
                    # Otherwise, mark first day of month
                    tLength = (calendar.monthrange(single_date.year, single_date.month)[1] / float(daycount)) * 100.0
                    filecontent += '''
                        <div class="month_mark" style="left: ''' + str(tLeft) + '''%; width: ''' + str(tLength) + '''%;">
                            <div class="caption">''' + single_date.strftime("%b %Y") + '''</div>
                        </div>
                    '''

            
            filecontent += '''
                </div>
                '''
            
            tasksprint = ""
            milestonesprint = ""

            # Write all tasks
            for task in realEntities:
                if (type(task).__name__ == "Task"):
                    if (task['start_date'] != None and task['end_date'] != None):
                        # Task with defined dates: Calculate ranges
                        tStartDate = datetime.datetime(task['start_date'].year, task['start_date'].month, task['start_date'].day, task['start_date'].hour, task['start_date'].minute)
                        tEndDate = datetime.datetime(task['end_date'].year, task['end_date'].month, task['end_date'].day, task['end_date'].hour, task['end_date'].minute)

                        tLeft = ((tStartDate - minDate).days / float(daycount)) * 100.0
                        tLength = ((tEndDate - tStartDate).days / float(daycount)) * 100.0
                    

                        tasksprint += '''
                            <div class="task" style="left: ''' + str(tLeft) + '''%; width: ''' + str(tLength) + '''%; background-color: ''' + task['type']['color'] + '''C0;">
                                <div class="name">''' + task['name'] + '''</div>
                                <div class="start">''' + task['start_date'].strftime("%Y/%m/%d") + '''</div>
                                <div class="end">''' + task['end_date'].strftime("%Y/%m/%d") + '''</div>
                                <div class="type">''' + task['type']['name'] + '''</div>
                            </div>
                        '''
                    else:
                        # Task without defined dates
                        
                        if (task['end_date'] != None):
                            # Task with an end date, but no start date
                            tEndDate = datetime.datetime(task['end_date'].year, task['end_date'].month, task['end_date'].day, task['end_date'].hour, task['end_date'].minute)
                            tLeft = ((tEndDate - minDate).days / float(daycount)) * 100.0
                            tLength = 15

                            if (tLeft - tLength < 0):
                                tLength = tLeft
                                tLeft = 0
                            else:
                                tLeft = tLeft - tLength

                            tasksprint += '''
                            <div class="task" style="left: ''' + str(tLeft) + '''%; width: ''' + str(tLength) + '''%; background-color: ''' + task['type']['color'] + '''C0; border-left: 0pt;">
                                <div class="name">''' + task['name'] + '''</div>
                                <div class="end">''' + task['end_date'].strftime("%Y/%m/%d") + '''</div>
                                <div class="type">''' + task['type']['name'] + '''</div>
                            </div>
                            '''
                        elif (task['start_date'] != None):
                            # Task with an start date, but no end date
                            tStartDate = datetime.datetime(task['start_date'].year, task['start_date'].month, task['start_date'].day, task['start_date'].hour, task['start_date'].minute)
                            tLeft = ((tStartDate - minDate).days / float(daycount)) * 100.0
                            tLength = 15

                            if (tLeft + tLength > 100):
                                tLength = 100 - tLeft

                            tasksprint += '''
                            <div class="task" style="left: ''' + str(tLeft) + '''%; width: ''' + str(tLength) + '''%; background-color: ''' + task['type']['color'] + '''C0; border-right: 0pt;">
                                <div class="name">''' + task['name'] + '''</div>
                                <div class="start">''' + task['start_date'].strftime("%Y/%m/%d") + '''</div>
                                <div class="type">''' + task['type']['name'] + '''</div>
                            </div>
                            '''
                        else:
                            tLeft = 0
                            tLength = 100

                            tasksprint += '''
                            <div class="task" style="left: ''' + str(tLeft) + '''%; width: ''' + str(tLength) + '''%; background-color: ''' + task['type']['color'] + '''C0;">
                                <div class="name">''' + task['name'] + '''</div>
                                <div class="type">''' + task['type']['name'] + '''</div>
                            </div>
                            '''

                elif (type(task).__name__ == "Milestone" and task['end_date'] != None):
                    # Handling milestones (but only if they have a date)

                    tStartDate = datetime.datetime(task['end_date'].year, task['end_date'].month, task['end_date'].day, task['end_date'].hour, task['end_date'].minute)
                    tLeft = ((tStartDate - minDate).days / float(daycount)) * 100.0
                    tLength = 15

                    if (tLeft + tLength > 100):
                        tLength = 100 - tLeft

                    milestonesprint += '''
                            <div class="milestone" style="left: ''' + str(tLeft) + '''%; width: ''' + str(tLength) + '''%; background-color: ''' + task['type']['color'] + '''C0;">
                                <div class="caption">''' + task['name'] + '''</div>
                                <div class="end">''' + task['end_date'].strftime("%Y/%m/%d") + '''</div>
                            </div>
                            <div class="milestone_bar" style="left: ''' + str(tLeft) + '''%;"></div>
                            '''
                    
            # Apply
            
            filecontent += '''
                <div id="milestones">
                    ''' + milestonesprint + '''
                </div>
                <div id="tasks">
                    ''' + tasksprint + '''
                </div>
                '''


            # General ending

            filecontent += '''
                    </div>
                </div>
            </html>
            '''

            # Generate unique temp file name
            file_path = tempfile.NamedTemporaryFile(
                prefix='gantt_export_', 
                suffix='.html', 
                delete=False
            ).name

            # Write to file
            f=open(file_path,"w")
            f.write(filecontent)
            f.close()

            # Create file component for job
            job_file = os.path.basename(file_path).replace('.html', '')
            component = session.create_component(
                file_path,
                data={'name': job_file},
                location=session.query(u"Location where name is 'ftrack.server'").one()
            )
            session.commit()

            # Attach to job
            session.create(
                'JobComponent',
                {
                    'component_id': component['id'], 
                    'job_id': job['id']
                }
            )
            
            # Set job status as done
            job['status'] = 'done'
            job['data'] = json.dumps({
                'description': 'Gantt Chart exported'
            })
            session.commit()

        except BaseException as exc:
            # Error handling: Write error
            self.logger.exception('Exporting Gantt Chart failed')
            session.rollback()
            job['status'] = 'failed'
            job['data'] = json.dumps({
                'description': exc.message
            })
            session.commit()

            















    


    ##############################################################################
    #                                                                            #
    # You do not need to edit something below, as these are just utility methods #
    #                   for discovery, registration and more                     #
    #                                                                            #
    ##############################################################################


    @property
    def session(self):
        '''Return convenient exposure of the self._session reference.'''
        return self._session

    @property
    def ftrack_server_location(self):
        '''Return the ftrack.server location.'''
        return self.session.query(
            u"Location where name is 'ftrack.server'"
        ).one()


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

    action_handler = unexCreateGanttChartAction(session)
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

