# Event Tree Visualizer

A simple visualization tool for event trees in XML format as uploaded on [OpenPRA Org](https://github.com/openpra-org/generic-pwr-openpsa-model/tree/a795d2c3ae5fd153d03475c1a15660cc90f33b44/models). This application takes XML event tree definitions and creates an interactive visual representation.

## Prerequisites

- Node.js (v16 or later)
- npm or yarn

## Setup Instructions for Mac Silicon

1. Clone the repository:
```bash
git clone <repository-url>
cd event-tree-visualizer
```

2. Install dependencies:
```bash
npm install
# or
yarn install
```

3. Install required UI components:
```bash
npm install @/components/ui
# or
yarn add @/components/ui
```

## Usage

1. Place your XML file in the project directory.

2. Update the file path in `EventTreeDiagram.jsx`:
```javascript
const response = await window.fs.readFile('your-file-name.xml', { encoding: 'utf8' });
```

3. Update the event tree name if different from 'EQK-BIN1':
```javascript
const eventTreeElement = xmlDoc.querySelector('define-event-tree[name="YOUR-TREE-NAME"]');
```

4. Start the development server:
```bash
npm run dev
# or
yarn dev
```

5. Open your browser and navigate to `http://localhost:3000`

## Input Format Requirements

1. XML file should follow the OpenPSA MEF format
2. Must contain a `define-event-tree` element with the specified name
3. Event tree should include:
   - Functional events with labels
   - Path definitions with success/failure states
   - Sequence definitions

## Example XML Structure

```xml
<opsa-mef>
    <define-event-tree name="EQK-BIN1">
        <define-functional-event name="FE12">
            <label>CD-EQ1-FT</label>
        </define-functional-event>
        ...
    </define-event-tree>
</opsa-mef>
```

## Troubleshooting

- If you see a blank screen, check the browser console for errors
- Verify that your XML file is properly formatted
- Ensure all dependencies are correctly installed
- Check that the event tree name matches exactly with your XML file


https://claude.ai/chat/574c533b-0fd8-4bef-ad27-401c4d98db59