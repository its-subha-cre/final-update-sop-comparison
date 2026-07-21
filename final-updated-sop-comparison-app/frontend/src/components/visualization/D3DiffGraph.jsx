import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { FileText, Cpu, AlertTriangle } from 'lucide-react';

export default function D3DiffGraph({ activeJob }) {
  const svgRef = useRef(null);
  const [hasData, setHasData] = useState(false);

  useEffect(() => {
    // Only verify activeJob state here. svgRef.current is always mounted now.
    if (!activeJob || activeJob.status !== 'completed' || !svgRef.current) {
      setHasData(false);
      return;
    }

    setHasData(true);

    const report = activeJob.report || {};
    const sopResults = report.sop_results || {};
    const localKeys = Object.keys(sopResults);

    // 1. Build simple high-level document nodes
    const nodes = [
      { id: 'global', label: 'Global Standard', name: 'Global SOP Standard', isGlobal: true }
    ];

    const links = [];

    localKeys.forEach((key, idx) => {
      const sop = sopResults[key];
      const localId = `local-${idx}`;
      nodes.push({
        id: localId,
        label: 'Local SOP',
        name: sop.name,
        match: `${sop.similarity_score}% Match`,
        isGlobal: false
      });
      links.push({
        source: 'global',
        target: localId
      });
    });

    // 2. Clear previous canvas
    d3.select(svgRef.current).selectAll('*').remove();

    const width = 600;
    const height = 320; // Perfect responsive height to fill available viewport card

    const svg = d3.select(svgRef.current)
      .attr('width', '100%')
      .attr('height', '100%')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .style('background', 'rgba(11, 8, 22, 0.45)')
      .style('border-radius', '12px')
      .style('border', '1px solid rgba(255, 255, 255, 0.05)');

    // 3. Dynamic Zoom and spacing calculation based on node count
    const nodeCount = nodes.length;
    let linkDistance = 120;
    let chargeStrength = -150;

    if (nodeCount <= 2) {
      linkDistance = 160; // Zoom in / increase spacing for few nodes
      chargeStrength = -250;
    } else if (nodeCount > 5) {
      linkDistance = 90; // Zoom out / decrease spacing for many nodes
      chargeStrength = -100;
    }

    // 4. Create force simulation optimized to keep nodes perfectly centered
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(linkDistance))
      .force('charge', d3.forceManyBody().strength(chargeStrength))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('x', d3.forceX(width / 2).strength(0.25)) // Centering gravity X
      .force('y', d3.forceY(height / 2).strength(0.25)) // Centering gravity Y
      .force('collision', d3.forceCollide().radius(40));

    // 5. Draw connection links
    const link = svg.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', 'rgba(139, 92, 246, 0.45)')
      .attr('stroke-width', 2.5)
      .style('stroke-dasharray', '4,4');

    // 6. Node containers
    const node = svg.append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .call(drag(simulation));

    // Glow effects definitions
    const defs = svg.append('defs');
    
    // Global node glow (purple)
    const globalGlow = defs.append('filter').attr('id', 'global-glow');
    globalGlow.append('feGaussianBlur').attr('stdDeviation', '6').attr('result', 'coloredBlur');
    const globalMerge = globalGlow.append('feMerge');
    globalMerge.append('feMergeNode').attr('in', 'coloredBlur');
    globalMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    // Local node glow (cyan)
    const localGlow = defs.append('filter').attr('id', 'local-glow');
    localGlow.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'coloredBlur');
    const localMerge = localGlow.append('feMerge');
    localMerge.append('feMergeNode').attr('in', 'coloredBlur');
    localMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    // 7. Draw circles
    node.append('circle')
      .attr('r', d => d.isGlobal ? 20 : 14)
      .attr('fill', d => d.isGlobal ? '#8b5cf6' : '#06b6d4')
      .attr('filter', d => d.isGlobal ? 'url(#global-glow)' : 'url(#local-glow)')
      .attr('stroke', 'rgba(255, 255, 255, 0.35)')
      .attr('stroke-width', 1.5)
      .style('cursor', 'grab');

    // 8. Draw Labels (Filenames)
    node.append('text')
      .text(d => d.name.length > 20 ? d.name.substring(0, 20) + '...' : d.name)
      .attr('y', d => d.isGlobal ? -28 : -22)
      .attr('text-anchor', 'middle')
      .attr('fill', 'rgba(255, 255, 255, 0.95)')
      .style('font-size', '9.5px')
      .style('font-weight', '600')
      .style('font-family', 'sans-serif')
      .style('pointer-events', 'none')
      .style('text-shadow', '0 2px 4px rgba(0,0,0,0.85)');

    // 9. Draw Sub-labels (Scores for local documents)
    node.filter(d => !d.isGlobal).append('text')
      .text(d => d.match)
      .attr('y', 24)
      .attr('text-anchor', 'middle')
      .attr('fill', 'var(--secondary)')
      .style('font-size', '9px')
      .style('font-weight', '700')
      .style('font-family', 'sans-serif')
      .style('pointer-events', 'none')
      .style('text-shadow', '0 1px 3px rgba(0,0,0,0.9)');

    // 10. Update positions with strict bounding box constraints to prevent clipping
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      node
        .attr('transform', d => {
          const paddingX = 85; // Extra padding for file names
          const paddingY = 40;
          d.x = Math.max(paddingX, Math.min(width - paddingX, d.x));
          d.y = Math.max(paddingY, Math.min(height - paddingY, d.y));
          return `translate(${d.x}, ${d.y})`;
        });
    });

    function drag(sim) {
      function dragstarted(event) {
        if (!event.active) sim.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      }
      function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      }
      function dragended(event) {
        if (!event.active) sim.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
      }
      return d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended);
    }
  }, [activeJob]);

  const hasNeo4jWarning = activeJob?.errors?.some(err => err.toLowerCase().includes('neo4j')) || false;

  return (
    <div className="glass" style={{
      padding: '24px',
      textAlign: 'left',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      minHeight: '480px',
      boxSizing: 'border-box'
    }}>
      {/* Header spacing */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
        <div>
          <h3 style={{ marginTop: 0, marginBottom: '6px', fontSize: '15px' }} className="gradient-text">Document Mapping Overview</h3>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0 }}>
            High-level document association tree. Drag nodes to inspect local SOP matches relative to the Global Standard.
          </p>
        </div>
        {hasNeo4jWarning && (
          <span style={{
            fontSize: '9px', fontWeight: 700, padding: '3px 8px', borderRadius: '4px',
            background: 'rgba(239, 68, 68, 0.08)', color: '#fca5a5', border: '1px solid rgba(239, 68, 68, 0.18)',
            whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: '4px'
          }}>
            <AlertTriangle style={{ width: '12px', height: '12px', color: 'var(--error)' }} />
            Neo4j Offline
          </span>
        )}
      </div>

      {/* Graph container - always mounted to prevent ref from being null */}
      <div style={{
        flex: 1,
        display: hasData ? 'flex' : 'none',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(0,0,0,0.1)',
        borderRadius: '12px',
        border: '1px solid rgba(255,255,255,0.02)',
        padding: '12px',
        overflow: 'hidden'
      }}>
        <svg ref={svgRef} style={{ width: '100%', height: '100%' }}></svg>
      </div>

      {/* Dynamic Empty State Placeholder */}
      {!hasData && (
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'rgba(0,0,0,0.15)',
          borderRadius: '12px',
          border: '1px dashed rgba(255,255,255,0.08)',
          padding: '40px',
          color: 'var(--text-muted)',
          textAlign: 'center'
        }}>
          <div style={{
            width: '54px',
            height: '54px',
            borderRadius: '50%',
            background: 'rgba(255,255,255,0.03)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '16px',
            border: '1px solid rgba(255,255,255,0.05)'
          }}>
            <FileText style={{ width: '22px', height: '22px', color: 'var(--text-muted)' }} />
          </div>
          <h4 style={{ margin: '0 0 6px 0', fontSize: '14px', fontWeight: 600, color: 'white' }}>
            No Document Mapping Available Yet
          </h4>
          <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-muted)', lineHeight: '1.6', maxWidth: '300px' }}>
            Upload global and local SOPs to generate the interactive relationship graph.
          </p>
        </div>
      )}
    </div>
  );
}
