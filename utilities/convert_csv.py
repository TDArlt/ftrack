# Definitions (this is what you might want to change)
# Please make sure these exist. Otherwise you will get very strange results...

#: Delimter for given csv
csvDelimiter = ';'

#: This is the headline in csv for the column of the types
nameForType = 'Lstg. Art'
#: This is the headline in csv for the column of the texts/descriptions
nameForDescription = 'Text'
#: This is the headline in csv for the column of the bidding amount
nameForBid = 'KV Menge'
#: Defines the type name of a row that is used as headline
typeNameIfHeadline = ''
#: Defines, if the bidding is done in hours or days
bidIsInHours = True
#: Defines how many hours should be calculated as a whole work day
hoursPerDay = 8
#: Defines, if the numbers are written with a comma instead of a dot
numbersUseComma = True

#: Matching table for types
typeMatchingTable = {
    '3D-Grafik': 'Compositing',
    '3D-Graphic': 'Compositing',
    '2D-Compositing': 'Compositing',
    '3D-Datenkonvertierung': 'Modeling',
    '3D-Data conversion': 'Modeling',
    '3D-Modeling': 'Modeling',
    '3D-Texturing': 'Shading',
    '3D-Animation': 'Animation',

    'Beratung und Konzeption': 'Allgemein',
    'Projektabwicklung': 'Production',
    'Project handling': 'Production',
    'Projektmanagement': 'Production',
    'Project management': 'Production',

    'Layout creation': 'Previz',
    'Layout-Gestaltung': 'Previz',

    'Data handling': 'Modeling',
    'Datenhandling': 'Modeling',

    'Editing': 'Editing',
    'Encoding': 'Editing',

    'Rendering': 'Rendering',
    'Rendermanagement': 'Rendering',
    'Render management': 'Rendering',

    'Programming': 'Feature',
    'Programmierung': 'Feature',
    'Programmtests': 'Test',
    'Software testing': 'Test',
}

# Now, the rest should be working by itself


import csv
import os

columnIdType = 0
columnIdDescription = 0
columnIdBid = 0


# Get file
inputfile = input('Please enter a csv table to parse: ')

inputfilename, inputfileextension = os.path.splitext(inputfile)
outputfilename = inputfilename + '_ftrack.csv'


inputlines = []


with open(inputfile, 'r') as csvfile:
    csvreader = csv.reader(csvfile, delimiter=csvDelimiter) 
    for row in csvreader:
        inputlines.append(row)
    


# Prepare output
#outputlines = ['Seq. name', 'Shot name', 'Bid', 'Type', 'Description']
outputlines = [['Information Name', 'Task Name', 'Task Bid days', 'Task Type', 'Task Description']]
currentHeading = ""

for linenum in range(len(inputlines)):
    if (linenum == 0):
        # First line includes the heading. That's where we look for everything
        columnIdType = inputlines[linenum].index(nameForType)
        columnIdDescription = inputlines[linenum].index(nameForDescription)
        columnIdBid = inputlines[linenum].index(nameForBid)
    else:
        # Every other line: Convert
        if typeNameIfHeadline == inputlines[linenum][columnIdType]:
            # We have a headline here. Use that one
            currentHeading = inputlines[linenum][columnIdDescription]
        else:
            # Every other line: Parse content

            # Get bidding number
            bidnumber = inputlines[linenum][columnIdBid]
            if (numbersUseComma):
                bidnumber = bidnumber.replace(',', '.')
            
            bidnumber = float(bidnumber)

            if bidIsInHours:
                bidnumber = bidnumber / hoursPerDay

            # Try to match type
            typeName = inputlines[linenum][columnIdType]
            if typeName in typeMatchingTable:
                typeName = typeMatchingTable[typeName]

            # Group name | Task name | Bid | Type | Description
            outputlines.append([
                currentHeading,
                inputlines[linenum][columnIdType],
                "{0:.2f}".format(bidnumber),
                typeName,
                inputlines[linenum][columnIdDescription]
            ])



with open(outputfilename, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(outputlines)

print ("Converted the csv and saved to {0}".format(outputfilename))

# Push full string into clipboard.
# unfortunately, this does not work in native python
try:
    import pyperclip

    fullstring = ""
    with open(outputfilename, "r") as f:
        fullstring = "".join(f.readlines())

    pyperclip.copy(fullstring)
    
    print ("Copied the content to your clipboard")
except:
    pass

input('Hit enter to close window.')