'use client';

import { useEffect, useRef } from 'react';

interface Job {
  job_id: number;
  status: string;
  command: string;
  group_name: string;
  depends_on: string[];
}

interface JobGraphProps {
  jobs: Job[];
}

export function JobGraph({ jobs }: JobGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || jobs.length === 0) return;

    const svg = svgRef.current;
    const width = 500;
    const height = 400;
    
    // Clear previous content
    svg.innerHTML = '';
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

    // Create job nodes with positions
    const nodes = jobs.map((job, index) => {
      // Arrange in a grid-like pattern
      const cols = Math.ceil(Math.sqrt(jobs.length));
      const row = Math.floor(index / cols);
      const col = index % cols;
      
      return {
        ...job,
        x: (col + 1) * (width / (cols + 1)),
        y: (row + 1) * (height / (Math.ceil(jobs.length / cols) + 1)),
        id: job.job_id.toString()
      };
    });

    // Create a map for quick node lookup
    const nodeMap = new Map(nodes.map(node => [node.id, node]));

    // Draw connections first (so they appear behind nodes)
    jobs.forEach(job => {
      const targetNode = nodeMap.get(job.job_id.toString());
      if (!targetNode) return;

      job.depends_on.forEach(depId => {
        const sourceNode = nodeMap.get(depId);
        if (sourceNode) {
          // Draw arrow from source to target
          const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
          line.setAttribute('x1', sourceNode.x.toString());
          line.setAttribute('y1', sourceNode.y.toString());
          line.setAttribute('x2', targetNode.x.toString());
          line.setAttribute('y2', targetNode.y.toString());
          line.setAttribute('stroke', '#6b7280');
          line.setAttribute('stroke-width', '2');
          line.setAttribute('marker-end', 'url(#arrowhead)');
          svg.appendChild(line);
        }
      });
    });

    // Add arrowhead marker definition
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
    marker.setAttribute('id', 'arrowhead');
    marker.setAttribute('markerWidth', '10');
    marker.setAttribute('markerHeight', '7');
    marker.setAttribute('refX', '9');
    marker.setAttribute('refY', '3.5');
    marker.setAttribute('orient', 'auto');
    
    const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    polygon.setAttribute('points', '0 0, 10 3.5, 0 7');
    polygon.setAttribute('fill', '#6b7280');
    
    marker.appendChild(polygon);
    defs.appendChild(marker);
    svg.appendChild(defs);

    // Draw nodes on top
    nodes.forEach(node => {
      const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      group.setAttribute('transform', `translate(${node.x}, ${node.y})`);

      // Node circle
      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('r', '25');
      circle.setAttribute('stroke', '#374151');
      circle.setAttribute('stroke-width', '2');
      
      // Color based on status
      const fillColor = {
        'COMPLETED': '#22c55e',
        'RUNNING': '#3b82f6',
        'PENDING': '#f59e0b',
        'FAILED': '#ef4444',
        'BLOCKED': '#8b5cf6'
      }[node.status] || '#6b7280';
      
      circle.setAttribute('fill', fillColor);
      circle.setAttribute('opacity', '0.8');
      
      // Add hover effect
      circle.addEventListener('mouseenter', () => {
        circle.setAttribute('opacity', '1');
        circle.setAttribute('r', '30');
      });
      
      circle.addEventListener('mouseleave', () => {
        circle.setAttribute('opacity', '0.8');
        circle.setAttribute('r', '25');
      });

      group.appendChild(circle);

      // Job ID text
      const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('dy', '0.3em');
      text.setAttribute('fill', 'white');
      text.setAttribute('font-size', '12');
      text.setAttribute('font-weight', 'bold');
      text.textContent = node.job_id.toString().slice(-4); // Last 4 digits
      group.appendChild(text);

      // Tooltip
      const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
      title.textContent = `Job ${node.job_id}: ${node.status}\n${node.command}`;
      group.appendChild(title);

      svg.appendChild(group);
    });

  }, [jobs]);

  if (jobs.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        No jobs to display
      </div>
    );
  }

  return (
    <div className="w-full">
      <svg
        ref={svgRef}
        className="w-full h-96 border border-gray-200 rounded-lg bg-gray-50"
        style={{ maxWidth: '100%', height: '400px' }}
      />
      <div className="mt-4 flex flex-wrap gap-4 text-xs">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-green-500"></div>
          <span>Completed</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-blue-500"></div>
          <span>Running</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
          <span>Pending</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-red-500"></div>
          <span>Failed</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-purple-500"></div>
          <span>Blocked</span>
        </div>
      </div>
    </div>
  );
}