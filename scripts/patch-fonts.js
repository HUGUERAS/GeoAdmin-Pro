#!/usr/bin/env node
// Patch Expo web dist: move icon fonts out of node_modules paths
// so Vercel serves them correctly (Vercel blocks /node_modules/ paths)

const fs = require('fs');
const path = require('path');

const distDir = path.join(__dirname, '..', 'mobile', 'dist');
const fontSrc = path.join(
  distDir, 'assets', 'node_modules', '@expo', 'vector-icons',
  'build', 'vendor', 'react-native-vector-icons', 'Fonts'
);
const fontDest = path.join(distDir, '_expo', 'static', 'media');

fs.mkdirSync(fontDest, { recursive: true });

if (fs.existsSync(fontSrc)) {
  const fonts = fs.readdirSync(fontSrc).filter(f => f.endsWith('.ttf'));
  for (const font of fonts) {
    fs.copyFileSync(path.join(fontSrc, font), path.join(fontDest, font));
  }
  console.log(`Copied ${fonts.length} fonts to _expo/static/media/`);
}

const bundleDir = path.join(distDir, '_expo', 'static', 'js', 'web');
if (!fs.existsSync(bundleDir)) process.exit(0);

const oldPath = '/assets/node_modules/@expo/vector-icons/build/vendor/react-native-vector-icons/Fonts/';
const newPath = '/_expo/static/media/';

const bundles = fs.readdirSync(bundleDir).filter(f => f.startsWith('entry-') && f.endsWith('.js'));
for (const bundle of bundles) {
  const p = path.join(bundleDir, bundle);
  const content = fs.readFileSync(p, 'utf8');
  const patched = content.split(oldPath).join(newPath);
  if (patched !== content) {
    fs.writeFileSync(p, patched);
    console.log(`Patched font paths in ${bundle}`);
  }
}
