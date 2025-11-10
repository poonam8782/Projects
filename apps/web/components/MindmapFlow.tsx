"use client";
import React, { useMemo } from 'react';
import ReactFlow, { Background, Controls, MiniMap, Node, Edge, Position } from 'reactflow';
import dagre from '@dagrejs/dagre';
import 'reactflow/dist/style.css';
import type { MindmapNode } from '@/services/api';

const NODE_W = 200;
const NODE_H = 54;

function toGraph(root: MindmapNode) {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  function walk(n: MindmapNode, parent?: MindmapNode) {
    nodes.push({
      id: n.id,
      data: { label: n.label },
      position: { x: 0, y: 0 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: {
        width: NODE_W,
        height: NODE_H,
        borderRadius: 8,
        padding: 8,
        background: '#ffffff',
        border: '1px solid #e5e7eb',
        fontSize: 12,
        lineHeight: 1.2,
        boxShadow: '0 1px 2px rgba(0,0,0,0.08)'
      }
    });
    (n.children || []).forEach(child => {
      edges.push({ id: `${n.id}->${child.id}`, source: n.id, target: child.id });
      walk(child, n);
    });
  }
  walk(root);
  return { nodes, edges };
}

function layout(nodes: Node[], edges: Edge[], rankdir: 'LR' | 'TB' = 'LR') {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir, nodesep: 60, ranksep: 90, marginx: 40, marginy: 40 });
  g.setDefaultEdgeLabel(() => ({}));
  nodes.forEach(n => g.setNode(n.id, { width: NODE_W, height: NODE_H }));
  edges.forEach(e => g.setEdge(e.source, e.target));
  dagre.layout(g);
  return {
    nodes: nodes.map(n => {
      const { x, y } = g.node(n.id);
      return { ...n, position: { x: x - NODE_W / 2, y: y - NODE_H / 2 } };
    }),
    edges
  };
}

export default function MindmapFlow({ root }: { root: MindmapNode }) {
  const { nodes, edges } = useMemo(() => {
    const g = toGraph(root);
    return layout(g.nodes, g.edges, 'LR');
  }, [root]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      fitView
      minZoom={0.2}
      maxZoom={3}
      proOptions={{ hideAttribution: true }}
    >
      <MiniMap pannable zoomable />
      <Controls showInteractive={false} />
  <Background gap={16} size={1} />
    </ReactFlow>
  );
}
