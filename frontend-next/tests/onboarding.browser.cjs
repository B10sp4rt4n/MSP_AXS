const fs=require('fs'),path=require('path'),ts=require('typescript'),assert=require('node:assert/strict');
const {chromium}=require('playwright');const modules=[],ids=new Map();
const mocks={'@/lib/api':`exports.api={post:async(p,b)=>{window.calls.push({p,b});if(window.pause)await new Promise(r=>window.release=r);if(window.fail)throw Error('Resultado incierto');return {status:'accepted'};}};`};
function bundle(name,parent=path.join(process.cwd(),'entry.js')){
 const f=mocks[name]?name:name.startsWith('@/')?require.resolve(path.join(process.cwd(),'src',name.slice(2))+ (fs.existsSync(path.join(process.cwd(),'src',name.slice(2))+'.tsx')?'.tsx':'.ts')):(name.startsWith('.') && fs.existsSync(path.resolve(path.dirname(parent),name)+'.tsx') ? path.resolve(path.dirname(parent),name)+'.tsx' : require.resolve(name,{paths:[path.dirname(parent)]}));
 if(ids.has(f))return ids.get(f);const id=modules.length;ids.set(f,id);modules.push('');
 let s=mocks[name]||fs.readFileSync(f,'utf8');if(/\.tsx?$/.test(f))s=ts.transpileModule(s,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2020}}).outputText;
 s=s.replace(/process\.env\.NODE_ENV/g,'"production"').replace(/require\(["']([^"']+)["']\)/g,(_,d)=>`require(${bundle(d,f)})`);
 modules[id]=`function(require,module,exports){${s}\n}`;return id;
}
(async()=>{
 const dom=bundle('react-dom'),r=bundle('react'),d=bundle('react-dom/client'),c=bundle(path.join(process.cwd(),'src/components/IncorporacionResidentes.tsx'));
 const js=`const mods=[${modules.join(',')}],cache={};function require(id){if(!cache[id]){const m={exports:{}};cache[id]=m;mods[id](require,m,m.exports)}return cache[id].exports}const root=require(${d}).createRoot(document.getElementById('root'));const users=Array.from({length:3},(_,i)=>({usuario_id:'u'+i,nombre:'Residente '+i,email:'r'+i+'@example.com',rol:'RESIDENTE',casa_unidad:'00'+i,incorporacion:{estado:i===2?'registrado':'precargado',registro_completo:i===2,vivienda_valida:true,puede_invitar:i!==2,invitacion:{estado:'sin_solicitar',solicitada_en:null,vence_en:null}}}));window.renderTenant=t=>require(${dom}).flushSync(()=>root.render(require(${r}).createElement(require(${c}).default,{key:t,condominioId:t,usuarios:users,getToken:async()=>'synthetic',onRefresh:()=>{},loading:false})));window.renderTenant('a');`;
 const browser=await chromium.launch({headless:true});try{
 const page=await browser.newPage({viewport:{width:390,height:844}});
 await page.route('**/*',route=>route.request().url()==='http://127.0.0.1:47891/'?route.fulfill({contentType:'text/html',body:'<div id="root"></div>'}):route.abort());
 await page.goto('http://127.0.0.1:47891/');await page.evaluate(()=>window.calls=[]);await page.addScriptTag({content:js});
 await page.getByRole('checkbox').nth(0).check();await page.getByRole('checkbox').nth(1).check();assert.equal(await page.getByRole('checkbox').nth(2).isDisabled(),true);
 await page.getByRole('button',{name:'Revisar invitaciones seleccionadas'}).click();assert.equal(await page.evaluate(()=>window.calls.length),0);
 await page.getByRole('button',{name:'Confirmar y enviar invitaciones'}).click();await page.getByText('Resultado por destinatario',{exact:true}).waitFor();
 assert.equal(await page.evaluate(()=>window.calls.length),2);assert.equal(await page.evaluate(()=>window.calls[0].b.expected_email),'r0@example.com');
 await page.evaluate(()=>{window.renderTenant('b');window.calls=[];window.fail=true});
 await page.getByRole('checkbox').nth(0).check();await page.getByRole('checkbox').nth(1).check();await page.getByRole('button',{name:'Revisar invitaciones seleccionadas'}).click();await page.getByRole('button',{name:'Confirmar y enviar invitaciones'}).click();
 await page.getByText('r1@example.com: No intentado: lote detenido',{exact:true}).waitFor();assert.equal(await page.evaluate(()=>window.calls.length),1);
 await page.evaluate(()=>{window.renderTenant('c');window.calls=[];window.fail=false;window.pause=true});
 await page.getByRole('checkbox').nth(0).check();await page.getByRole('checkbox').nth(1).check();await page.getByRole('button',{name:'Revisar invitaciones seleccionadas'}).click();await page.getByRole('button',{name:'Confirmar y enviar invitaciones'}).click();await page.waitForFunction(()=>!!window.release);
 await page.evaluate(()=>window.renderTenant('d'));await page.getByRole('button',{name:'Revisar invitaciones seleccionadas'}).waitFor();await page.evaluate(()=>window.release());
 assert.equal(await page.evaluate(()=>window.calls.length),1);
 assert.equal(await page.getByText('Resultado por destinatario',{exact:true}).count(),0);
 console.log('PASS: selection, explicit review, saved email, registered exclusion, stop on failure, stop on tenant switch. Synthetic transport.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
