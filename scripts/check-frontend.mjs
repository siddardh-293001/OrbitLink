// Evaluate every imported application module, not just the entry file.
// React hooks/DOM are stubbed: this catches startup/module errors, not WebGL rendering.
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {readFileSync} from 'node:fs';
globalThis.React={createElement(){},useState(){},useEffect(){},useRef(){}};
globalThis.ReactDOM={createRoot(){return {render(){}}}};
globalThis.document={getElementById(){return {}}};
await import(pathToFileURL(resolve('frontend/app.js')));
const html=readFileSync('frontend/index.html','utf8');
for(const dependency of ['vendor/react.js','vendor/react-dom.js']){
 if(!html.includes(dependency))throw Error('Missing self-hosted dependency '+dependency);
 readFileSync(resolve('frontend',dependency));
}
console.log('PASS: complete frontend module graph and local entry dependencies');
