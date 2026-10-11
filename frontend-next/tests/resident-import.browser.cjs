const fs=require('fs'),path=require('path'),ts=require('typescript'),assert=require('node:assert/strict');
const {chromium}=require('playwright');const modules=[],ids=new Map();
const mocks={'@/lib/api':`exports.api={get:async()=>[],download:async()=>new Blob(['xlsx']),post:async(p,b)=>{window.calls.push({p,b});if(window.fail)throw Error('Vuelve a validar');return {filas:[{fila:2,vivienda:'001',nombre:'Ana',correo:'ana@example.com',estado:b.revision?'creado':'nuevo',errores:window.invalid?['Correo inválido']:[]}],revision:'rev1',nuevos:1,existentes:0,errores:window.invalid?1:0,confirmado:!!b.revision,creados:b.revision?1:0};}};`};
function bundle(name,parent=path.join(process.cwd(),'entry.js')){
 const f=mocks[name]?name:name.startsWith('@/')?require.resolve(path.join(process.cwd(),'src',name.slice(2))+ (fs.existsSync(path.join(process.cwd(),'src',name.slice(2))+'.tsx')?'.tsx':'.ts')):(name.startsWith('.') && fs.existsSync(path.resolve(path.dirname(parent),name)+'.tsx') ? path.resolve(path.dirname(parent),name)+'.tsx' : require.resolve(name,{paths:[path.dirname(parent)]}));
 if(ids.has(f))return ids.get(f);const id=modules.length;ids.set(f,id);modules.push('');
 let s=mocks[name]||fs.readFileSync(f,'utf8');if(/\.tsx?$/.test(f))s=ts.transpileModule(s,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2020}}).outputText;
 s=s.replace(/process\.env\.NODE_ENV/g,'"production"').replace(/require\(["']([^"']+)["']\)/g,(_,d)=>`require(${bundle(d,f)})`);
 modules[id]=`function(require,module,exports){${s}\n}`;return id;
}
(async()=>{
 const dom=bundle('react-dom'),r=bundle('react'),d=bundle('react-dom/client'),c=bundle(path.join(process.cwd(),'src/components/UsuariosCondominio.tsx'));
 const js=`const mods=[${modules.join(',')}],cache={};function require(id){if(!cache[id]){const m={exports:{}};cache[id]=m;mods[id](require,m,m.exports)}return cache[id].exports}const root=require(${d}).createRoot(document.getElementById('root'));const getToken=async()=>'synthetic';window.renderTenant=t=>require(${dom}).flushSync(()=>root.render(require(${r}).createElement(require(${c}).default,{condominioId:t,getToken})));window.renderTenant('a');`;
 const browser=await chromium.launch({headless:true});try{
 const page=await browser.newPage({viewport:{width:390,height:844}});
 await page.route('**/*',route=>route.request().url()==='http://127.0.0.1:47891/'?route.fulfill({contentType:'text/html',body:'<div id="root"></div>'}):route.abort());
 await page.goto('http://127.0.0.1:47891/');await page.evaluate(()=>window.calls=[]);await page.addScriptTag({content:js});
 const file={name:'residentes.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:Buffer.from('synthetic')};
 await page.getByLabel('Archivo de residentes').setInputFiles(file);
 await page.getByRole('button',{name:'Validar archivo',exact:true}).click();await page.getByRole('button',{name:'Confirmar 1 altas'}).waitFor();
 assert.equal(await page.evaluate(()=>window.calls.length),1);assert.equal(await page.evaluate(()=>window.calls[0].b.revision),undefined);
 await page.getByRole('button',{name:'Confirmar 1 altas'}).click();await page.getByText('1 residentes creados. 0 existentes. 0 filas con errores.',{exact:true}).waitFor();
 assert.equal(await page.evaluate(()=>window.calls[1].b.revision),'rev1');
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Descargar resultado CSV'}).click();assert.equal((await download).suggestedFilename(),'AXS_resultado_importacion.csv');
 await page.evaluate(()=>window.renderTenant('b'));await page.getByLabel('Archivo de residentes').waitFor();assert.equal(await page.getByRole('button',{name:'Descargar resultado CSV'}).count(),0);
 await page.evaluate(()=>window.invalid=true);await page.getByLabel('Archivo de residentes').setInputFiles(file);await page.getByRole('button',{name:'Validar archivo',exact:true}).click();await page.getByText('Correo inválido',{exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'Confirmar 1 altas'}).count(),0);
 await page.evaluate(()=>{window.invalid=false;window.fail=true});await page.getByRole('button',{name:'Validar archivo',exact:true}).click();await page.getByRole('alert').waitFor();assert.equal(await page.getByRole('button',{name:'Confirmar 1 altas'}).count(),0);
 console.log('PASS: preview, confirmation, parent refresh, CSV, tenant change, invalid rows, server error. Synthetic transport.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
