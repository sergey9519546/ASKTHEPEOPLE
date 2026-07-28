import fs from 'fs';
import path from 'path';

const files = [
  'Step1GraphBuild.vue',
  'Step2EnvSetup.vue',
  'Step3Simulation.vue',
  'Step4Report.vue',
  'Step5Interaction.vue'
];

files.forEach((filename) => {
  const filePath = path.join(process.cwd(), 'frontend', 'src', 'components', filename);
  if (!fs.existsSync(filePath)) return;

  let content = fs.readFileSync(filePath, 'utf8');

  // Replace common light colors in CSS and HTML template
  content = content.replace(/var\(--atp-white\)/g, 'var(--bg-color)');
  content = content.replace(/var\(--atp-black\)/g, 'var(--text-primary)');
  content = content.replace(/#ffffff/gi, 'var(--bg-color)');
  content = content.replace(/#f8fafc/gi, 'rgba(255, 255, 255, 0.03)');
  content = content.replace(/#f1f5f9/gi, 'rgba(255, 255, 255, 0.05)');
  content = content.replace(/#e2e8f0/gi, 'var(--border-color)');
  content = content.replace(/#cbd5e1/gi, 'var(--border-color)');
  content = content.replace(/#475569/gi, 'var(--text-secondary)');
  content = content.replace(/#64748b/gi, 'var(--text-secondary)');
  content = content.replace(/#94a3b8/gi, 'var(--text-secondary)');
  content = content.replace(/#334155/gi, 'var(--text-primary)');
  content = content.replace(/#0f172a/gi, 'var(--surface-color)');
  content = content.replace(/#1e293b/gi, 'rgba(255, 255, 255, 0.1)');

  fs.writeFileSync(filePath, content, 'utf8');
  console.log(`Updated ${filename} to dark mode.`);
});
