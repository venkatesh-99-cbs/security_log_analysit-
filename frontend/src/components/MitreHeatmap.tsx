import React from 'react';
import { MitreMapping } from '../types';

interface MitreHeatmapProps {
  mappings: MitreMapping[];
}

// Complete predefined taxonomy of MITRE tactics and techniques that are supported by the system
const TACTICS_CONFIG = [
  {
    id: 'TA0001',
    name: 'Initial Access',
    techniques: [
      { id: 'T1190', name: 'Exploit Public App' },
      { id: 'T1078', name: 'Valid Accounts' },
    ],
  },
  {
    id: 'TA0003',
    name: 'Persistence',
    techniques: [
      { id: 'T1136', name: 'Create Account' },
      { id: 'T1098', name: 'Account Manipulation' },
    ],
  },
  {
    id: 'TA0004',
    name: 'Privilege Escalation',
    techniques: [
      { id: 'T1548', name: 'Abuse Elevation' },
      { id: 'T1078', name: 'Valid Accounts' },
    ],
  },
  {
    id: 'TA0006',
    name: 'Credential Access',
    techniques: [
      { id: 'T1110', name: 'Brute Force' },
      { id: 'T1003', name: 'Credential Dumping' },
      { id: 'T1552', name: 'Unsecured Credentials' },
    ],
  },
  {
    id: 'TA0007',
    name: 'Discovery',
    techniques: [
      { id: 'T1046', name: 'Service Discovery' },
      { id: 'T1083', name: 'File Discovery' },
      { id: 'T1057', name: 'Process Discovery' },
    ],
  },
  {
    id: 'TA0008',
    name: 'Lateral Movement',
    techniques: [
      { id: 'T1021', name: 'Remote Services' },
      { id: 'T1075', name: 'Pass the Hash' },
    ],
  },
  {
    id: 'TA0040',
    name: 'Impact',
    techniques: [
      { id: 'T1499', name: 'Endpoint DoS' },
      { id: 'T1485', name: 'Data Destruction' },
    ],
  },
];

export const MitreHeatmap: React.FC<MitreHeatmapProps> = ({ mappings }) => {
  const activeTechniqueIds = new Set(mappings.map((m) => m.technique_id));

  return (
    <div className="w-full flex flex-col gap-4">
      <div className="flex justify-between items-center">
        <h4 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
          MITRE ATT&amp;CK Heatmap Matrix
        </h4>
        <span className="text-xs text-slate-500 font-medium">
          {mappings.length} technique(s) mapped
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-7 gap-3">
        {TACTICS_CONFIG.map((tactic) => {
          // Count active techniques in this tactic
          const activeCount = tactic.techniques.filter((tech) => activeTechniqueIds.has(tech.id)).length;
          
          return (
            <div key={tactic.id} className="flex flex-col gap-2 p-3 bg-slate-900 border border-slate-800 rounded-xl">
              <div className="flex justify-between items-center pb-2 border-b border-slate-800/80">
                <span className="text-xs font-bold text-slate-400 truncate pr-1" title={tactic.name}>
                  {tactic.name}
                </span>
                {activeCount > 0 && (
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500 glow-red animate-pulse-slow"></span>
                )}
              </div>
              
              <div className="flex flex-col gap-2 mt-1">
                {tactic.techniques.map((tech) => {
                  const isActive = activeTechniqueIds.has(tech.id);
                  return (
                    <div 
                      key={tech.id} 
                      className={`p-2 rounded-lg text-center flex flex-col gap-1 transition-all ${
                        isActive 
                          ? 'bg-red-500/10 border border-red-500/30 shadow-[0_0_8px_rgba(239,68,68,0.1)]' 
                          : 'bg-slate-950 border border-slate-800/40 opacity-55 hover:opacity-100'
                      }`}
                    >
                      <span className={`text-[10px] font-bold font-mono tracking-wider ${isActive ? 'text-red-400' : 'text-slate-500'}`}>
                        {tech.id}
                      </span>
                      <span className={`text-[11px] truncate leading-tight font-medium ${isActive ? 'text-red-200' : 'text-slate-400'}`} title={tech.name}>
                        {tech.name}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
