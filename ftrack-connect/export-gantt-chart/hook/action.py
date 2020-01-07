# :coding: utf-8
# :copyright: Copyright (c) 2019 c.arlt@unexpected.de
# :license: GPL-3.0

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

    def interface(self, session, entities, event):
        '''The user interface for our action

        *session* is a `ftrack_api.Session` instance

        *entities* is a list of tuples each containing the entity type and the entity id.
        If the entity is a hierarchical you will always get the entity
        type TypedContext, once retrieved through a get operation you
        will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.

        *event* the unmodified original event
        '''
        values = event['data'].get('values', {})

        firstObjInfo = getRealEntityFromTypedContext(session, entities[0])

        if (len(entities) == 1):
            if (type(firstObjInfo).__name__ == 'Project'):
                textDescription = 'Exporting a Gantt Chart for {0}'.format(firstObjInfo['full_name'])
            else:
                textDescription = 'Exporting a Gantt Chart for {0}'.format(firstObjInfo['name'])
        else:
            if (type(firstObjInfo).__name__ == 'Project'):
                textDescription = 'Exporting a Gantt Chart for {0} and {1} more'.format(firstObjInfo['full_name'], len(entities) -1)
            else:
                textDescription = 'Exporting a Gantt Chart for {0} and {1} more'.format(firstObjInfo['name'], len(entities) - 1)

        if not values:
            return [
                {
                    'type': 'label',
                    'value': textDescription
                },
                {
                    'type': 'label',
                    'value': '___'
                },
                {
                    'type': 'label',
                    'value': 'Properties for export:'
                },
                {
                    'label': 'Show assignees',
                    'type': 'boolean',
                    'name': 'show_assignees',
                    'value': 'False'
                },
                {
                    'label': 'Show current tasks\' status',
                    'type': 'boolean',
                    'name': 'show_status',
                    'value': 'False'
                },
                {
                    'type': 'label',
                    'value': '___'
                },
                {
                    'label': 'URL to custom CSS (if desired):',
                    'type': 'text',
                    'name': 'custom_css',
                    'value': ''
                }
            ]


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
        try:
            if 'values' in event['data']:
                self.logger.info(
                    u'Launching action with selection {0}'.format(entities)
                )

                data = event['data']
                logging.info(u'Launching action with data: {0}'.format(data))

                # Run exporter
                self.mainAsyncAction(entities, event['source']['user']['id'], data['values'])


                return {
                    'success': True,
                    'message': 'Export started...'
                }

        except BaseException as exc:
            return {
                    'success': False,
                    'message': exc.message.replace("<", "&lt;").replace(">", "&gt;")
                }
            


    ##############################################################################
    #                                                                            #
    #                           Space for custom methods                         #
    #                                                                            #
    ##############################################################################



    @async
    def mainAsyncAction(self, entities, user_id, settings):
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
            # TODO: What about connections between tasks? => Show arrows?
            # TODO: What about hierarchy (sort and show parent-grouping?)


    
            realEntities = []
            printString = ""
            headline = "Overview"

            for entity in entities:
                oneObject = getRealEntityFromTypedContext(session, entity)

                # Handling projects: We will need to get all the tasks of the project
                if type(oneObject).__name__ == "Project":
                    tasks = session.query('select id from Task where project.name is "' + oneObject['name'] + '"')
                    realEntities.extend(tasks)
                    milestones = session.query('select id from Milestone where project.name is "' + oneObject['name'] + '"')
                    realEntities.extend(milestones)

                    headline = oneObject['full_name']
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

            taskHeight = 38
            if settings['show_assignees']:
                taskHeight += 8

            # CSS
            cssStyle = '''
            body {
                font-family: 'Roboto', sans-serif;
                padding: 0pt;
                margin: 0pt;
            }
            .headline {
                font-size: 18pt;
                font-weight: bold;
                padding: 5pt;
                margin: 0pt;
            }

            @media print
            {    
                .no-print, .no-print *
                {
                    display: none !important;
                }
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
            .week_mark {
                padding-top: 12pt;
                border-left-color: #aaa;
                z-index: -5;
            }

            .task {
                margin: 0pt 0pt 2pt 0pt;
                padding: 5pt;
                height: ''' + str(taskHeight) + '''pt;
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

            .task .assigned {
                font-size: 7pt;
            }
            .task .assigned .user {
                font-size: 7pt;
                display: inline;
            }

            .task .status {
                font-size: 7pt;
                display: inline-block;
                border-radius: 2pt;
                padding: 2pt;
                position: absolute;
                top: 0pt;
                right: 0pt;
                opacity: 0.9;
                transition: all .3s;
            }
            .task .status:hover {
                opacity: 1;
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



            .scale {
                position: fixed;
                opacity: .2;
                top: 0pt;
                right: 0pt;
                width: 100pt;
                background-color: #fff;
                border: 1pt #000 solid;
                padding: 0pt;
                transition: all .3s;
                border-top: 0pt;
                border-right: 0pt;
                border-radius: 0pt 0pt 0pt 5pt;
            }

            .scale:hover {
                opacity: 1;
            }

            .scale input {
                width: 90pt;
                margin-left: 5pt;
            }


            '''

            # General beginning

            custom_css = ""
            if settings['custom_css'] != '':
                custom_css = '<link rel="stylesheet" href="' + settings['custom_css'] + '" />'

            filecontent = '''
            <html>
                <head>
                    <title>''' + headline + '''</title>
                    <meta charset="utf-8">
                    <link href="https://fonts.googleapis.com/css?family=Roboto&display=swap" rel="stylesheet"> 
                    <style>''' + cssStyle + '''</style>
                </head>
                <body>
                <div class="headline">''' + headline + '''</div>
                <div class="main" id="mainpage">
                    <div id="marks">
            '''

            # Write markers for weeks & months
            for single_date in daterange(minDate, maxDate):
                tLeft = ((single_date - minDate).days / float(daycount)) * 100.0

                # mark weekends
                if (single_date.weekday() == 5):
                    tLength = (2.0 / float(daycount)) * 100.0
                    filecontent += '''
                        <div class="weekend_mark" style="left: ''' + str(tLeft) + '''%; width: ''' + str(tLength) + '''%;"></div>
                    '''
                
                # mark each week beginning
                if (single_date.weekday() == 0):
                    tLength = (7.0 / float(daycount)) * 100.0
                    filecontent += '''
                        <div class="week_mark" style="left: ''' + str(tLeft) + '''%; width: ''' + str(tLength) + '''%;">
                            <div class="caption">''' + single_date.strftime("%m/%d") + '''</div>
                        </div>
                    '''
                
                if (single_date.day == 1):
                    # mark first day of month
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
                    statusText = ""
                    assigneesText = ""

                    if settings['show_status']:
                        statusText = '<div class="status" style="background-color: ' + task['status']['color'] + ';">' + task['status']['name'] + '</div>'
                    
                    if settings['show_assignees']:
                        assignedUsers = []

                        for assignment in task['assignments']:
                            if (type(assignment['resource']).__name__ == 'User'):
                                assignedUsers.append('<div class="user">' + assignment['resource']['first_name'] + " " + assignment['resource']['last_name'] + '</div>')
                        
                        if (len(assignedUsers) > 0):
                            assigneesText = '<div class="assigned">' + ', '.join(assignedUsers) + '</div>'
                        else:
                            assigneesText = '<div class="assigned">(unassigned)</div>'

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
                                ''' + statusText + assigneesText + '''
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
                                ''' + statusText + assigneesText + '''
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
                                ''' + statusText + assigneesText + '''
                            </div>
                            '''
                        else:
                            tLeft = 0
                            tLength = 100

                            tasksprint += '''
                            <div class="task" style="left: ''' + str(tLeft) + '''%; width: ''' + str(tLength) + '''%; background-color: ''' + task['type']['color'] + '''C0;">
                                <div class="name">''' + task['name'] + '''</div>
                                <div class="type">''' + task['type']['name'] + '''</div>
                                ''' + statusText + assigneesText + '''
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

                    <div class="no-print">
                        <div class="scale">
                            <input type="range" min="800" max="5000" value="50" class="slider" id="scaleRange" onchange="Scale()">
                        </div>
                        <script>

function Scale()
{
    document.getElementById("mainpage").style.width = document.getElementById("scaleRange").value + "px";
    UpdateWeekMarks();
}
function UpdateWeekMarks()
{
    marks = document.getElementsByClassName("week_mark");
    monthMarks = document.getElementsByClassName("month_mark");

    if (monthMarks.length > 0 && monthMarks[0].offsetWidth < 310)
    {
        for (i = 0; i < marks.length; i++)
        {
            marks[i].style.display = "none";
        }
    } else
    {
        for (i = 0; i < marks.length; i++)
        {
            marks[i].style.display = "block";
        }
    }
}

document.getElementById("scaleRange").value = document.getElementById("mainpage").offsetWidth;
UpdateWeekMarks();

                        </script>
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
            f.write(filecontent.encode('utf-8'))
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
                'description': exc.message.replace("<", "&lt;").replace(">", "&gt;")
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

