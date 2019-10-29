# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import sys
import logging
import argparse
import os
import glob

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

def get_filter_string(entity_ids):
    '''Return a comma separated string of quoted ids from *entity_ids* list.'''
    return ', '.join(
        '"{0}"'.format(entity_id) for entity_id in entity_ids
    )

class unexOpenFileAction(BaseAction):
    '''This action will open an associated rendering'''
    
    ##############################################################################
    #                                                                            #
    #                        Main parameters to be changed                       #
    #                                                                            #
    ##############################################################################

    #: entity property for file
    filePropertyName = 'associatedFile'

    #: If you like the first match to be shown, set to True. Otherwise the most recent file will be searched and shown
    takeFirstMatch = False

    #: The link to the external software
    viewerSoftware = "c:\\Program Files\\DJV\\bin\\djv_view.exe"

    #: The name of your main render pass (usually beauty or base)
    mainRenderpassName = "beauty"

    #: The name of the root for workflow directories
    workflowDirectoryName = "04_workflow"

    #: The name of the root for the render directories
    renderDirectoryName = "05_render"

    #: The sub-directories that exists in rendering; sort by priority if you like to get the first match only
    possibleRenderDirs = ['06_grading', '05_comp', '04_2d', '03_3d', '02_previews', '01_thumbnails']

    #: Action identifier.
    identifier = 'de.unexpected.ftrack.playrendering'

    #: Action label.
    label = 'Show Rendering'

    #: Action description
    description = 'Shows the associated rendering'

    #: Icon for this one
    icon = 'https://mediathek.unexpected.de/img/ftrack/play_sequence.png'





    #: The types of entities you like to support here
    SUPPORTED_ENTITY_TYPES = (
        'Task', 'TypedContext'
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

        # Only one element is supported and only the selected entity type
        if (len(entities) == 1):# and entities[0][0] in self.SUPPORTED_ENTITY_TYPES):
            # In general, we have a supported object here. Now, we need to check, if
            # there is an associated file here

            # Get real object
            oneObject = getRealEntityFromTypedContext(session, entities[0])
            if (self.filePropertyName in oneObject['custom_attributes']):
                return bool(oneObject['custom_attributes'][self.filePropertyName].strip())
            else:
                return False

        else:
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

        # Get real object
        oneObject = getRealEntityFromTypedContext(session, entities[0])
        
        # As we are very sure that this is valid, we may open the file directly
        filename = oneObject['custom_attributes'][self.filePropertyName]


        foundAFile = False


        # Find first element of hierarchy
        rootdirPos = filename.find(self.workflowDirectoryName + "\\")

        if (rootdirPos > -1):
            lookat = filename[rootdirPos + self.workflowDirectoryName.__len__() + 1:]

            # Look at the elements
            pathElements = lookat.split('\\')

            # First part is the software. This is something we don't need here
            # Second part is the type of our content. This is something we will need
            contentType = pathElements[1]

            # Third part is either a group or the object's name
            isGrouped = False
            groupName = ""
            contentName = ""
            if (contentType == "shots" and pathElements[2].startswith('seq_')) or (contentType == "assets" and pathElements[2].startswith('grp_')) or (contentType == "stills" and pathElements[2].startswith('grp_')):
                # This is a sequence or group and has another level
                isGrouped = True
                groupName = pathElements[2]
                contentName = pathElements[3]
            else:
                # Otherwise, we already have the object's name
                contentName = pathElements[2]

            # Ok, now build the first directory we like to look at
            finalFile = ""

            for renderDir in self.possibleRenderDirs:
                # Only continue looking, if we like to
                if (not foundAFile) or (not self.takeFirstMatch):
                    currentDir = os.path.join(filename[:(rootdirPos - filename.__len__())], self.renderDirectoryName, renderDir, contentType, contentName)
                    # If we are having a group here, we first need to check, if the dir is one level deeper
                    if isGrouped:
                        deeperDir = os.path.join(filename[:(rootdirPos - filename.__len__())], self.renderDirectoryName, renderDir, contentType, groupName, contentName)
                        if (os.path.isdir(deeperDir)):
                            currentDir = deeperDir

                    if (os.path.isdir(currentDir)):
                        # Get files and directories from here
                        files = []
                        dirs = []
                        for (dirpath, dirnames, filenames) in os.walk(currentDir):
                            files.extend(filenames)
                            dirs.extend(dirnames)
                        
                        # If there are no files, but directories
                        if (len(dirs) > 0):
                            # try to get the correct directory
                            for aDir in dirs:
                                # Only continue looking, if we like to
                                if (not foundAFile) or (not self.takeFirstMatch):
                                    if (self.mainRenderpassName in aDir):
                                        thisPath = os.path.join(currentDir, aDir)
                                        newest = max(glob.iglob(thisPath + '/*.*'), key=os.path.getmtime)

                                        if (not bool(finalFile) or os.path.getmtime(newest) < os.path.getmtime(finalFile)):
                                            finalFile = newest
                                            foundAFile = True


                        elif (len(files) > 0):
                            # We have files. Try to find the main pass
                            for aFile in files:
                                # Only continue looking, if we like to
                                if (not foundAFile) or (not self.takeFirstMatch):
                                    if (self.mainRenderpassName in aFile):
                                        newest = os.path.join(currentDir, aFile)

                                        if (not bool(finalFile) or os.path.getmtime(newest) < os.path.getmtime(finalFile)):
                                            finalFile = newest
                                            foundAFile = True






        # Check, if we are looking at a file or directory
        if (foundAFile):
            # Open file
            os.system('"%s" %s' % (self.viewerSoftware, finalFile))
            
            return {
                'success': True,
                'message': 'Opening the rendering for {0}'.format(oneObject['name'])
            }
        else:
            return {
                'success': False,
                'message': 'Could not find any rendering for {0}'.format(oneObject['name'])
            }





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

    action_handler = unexOpenFileAction(session)
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

