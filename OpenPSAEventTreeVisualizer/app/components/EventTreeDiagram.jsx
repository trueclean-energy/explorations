'use client'

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';

const EventTreeDiagram = () => {
  const [eventTree, setEventTree] = useState(null);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    const parseEventTree = async () => {
      try {
        const response = await fetch('/event.xml');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const xmlText = await response.text();
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
        
        // Find EQK-BIN1 event tree
        const eventTreeElement = xmlDoc.querySelector('define-event-tree[name="EQK-BIN1"]');
        if (eventTreeElement) {
          // Extract functional events
          const functionalEvents = Array.from(eventTreeElement.querySelectorAll('define-functional-event'))
            .map(event => ({
              name: event.getAttribute('name'),
              label: event.querySelector('label')?.textContent || ''
            }));
            
          // Extract sequences and paths
          const initialState = eventTreeElement.querySelector('initial-state');
          const paths = extractPaths(initialState);
          
          setEventTree({ functionalEvents, paths });
          setError(null);
        } else {
          setError('Could not find EQK-BIN1 event tree in the XML');
        }
      } catch (error) {
        console.error('Error parsing XML:', error);
        setError(`Error parsing the XML file: ${error.message}`);
      }
    };
    
    parseEventTree();
  }, []);

  // Function to recursively extract paths
  const extractPaths = (node, currentPath = []) => {
    if (!node) return [];
    
    const paths = [];
    const forks = node.querySelectorAll(':scope > fork');
    
    forks.forEach(fork => {
      const event = fork.getAttribute('functional-event');
      const pathElements = fork.querySelectorAll(':scope > path');
      
      pathElements.forEach(pathElement => {
        const state = pathElement.getAttribute('state');
        const sequence = pathElement.querySelector('sequence');
        
        const newPath = [...currentPath, { event, state }];
        
        if (sequence) {
          paths.push({
            steps: newPath,
            sequence: sequence.getAttribute('name')
          });
        }
        
        // Recursively process nested forks
        paths.push(...extractPaths(pathElement, newPath));
      });
    });
    
    return paths;
  };

  if (!eventTree) {
    return <div>Loading event tree...</div>;
  }

  const eventWidth = 150;
  const branchHeight = 80;
  const fontSize = "text-xs";

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>EQK-BIN1 Event Tree</CardTitle>
      </CardHeader>
      <CardContent className="overflow-auto">
        <div className="relative min-w-[800px]" style={{ minHeight: '600px' }}>
          {/* Event headers */}
          <div className="flex absolute top-0 left-0">
            <div className="w-20 p-2 border-r border-b font-semibold">Init</div>
            {eventTree.functionalEvents.map((event, idx) => (
              <div 
                key={event.name}
                className="border-r border-b p-2 font-semibold"
                style={{ width: eventWidth }}
              >
                <div className={fontSize}>{event.name}</div>
                <div className={fontSize}>{event.label}</div>
              </div>
            ))}
            <div className="w-24 p-2 border-b font-semibold">Sequence</div>
          </div>

          {/* Draw paths */}
          <div className="mt-12">
            {eventTree.paths.map((path, pathIdx) => {
              const y = (pathIdx + 1) * branchHeight;
              return (
                <div 
                  key={pathIdx}
                  className="absolute left-20 flex items-center"
                  style={{ top: `${y}px` }}
                >
                  {path.steps.map((step, stepIdx) => (
                    <div
                      key={stepIdx}
                      className="flex flex-col items-center justify-center border-b"
                      style={{ width: eventWidth }}
                    >
                      <div className={`${fontSize} py-1`}>
                        {step.state}
                      </div>
                      {/* Vertical connection line */}
                      {stepIdx < path.steps.length - 1 && (
                        <div className="absolute h-full border-r" 
                          style={{ 
                            left: `${(stepIdx + 1) * eventWidth + 20}px`,
                            top: '0px'
                          }} 
                        />
                      )}
                    </div>
                  ))}
                  {/* Empty spacer divs for remaining events */}
                  {Array(eventTree.functionalEvents.length - path.steps.length).fill(0).map((_, idx) => (
                    <div
                      key={`spacer-${idx}`}
                      style={{ width: eventWidth }}
                    />
                  ))}
                  {/* Sequence identifier */}
                  <div className={`${fontSize} ml-4`}>
                    {path.sequence}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default EventTreeDiagram;