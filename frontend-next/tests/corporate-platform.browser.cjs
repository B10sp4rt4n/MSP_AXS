// Synthetic Playwright: no external network, credentials, or operational tenant data.
const fs=require("fs"),path=require("path"),ts=require("typescript"),assert=require("node:assert/strict");
const {chromium}=require("playwright");
const modules=[],ids=new Map();
const mocks={
  "@clerk/nextjs":`const getToken=async()=> 'synthetic-token';exports.useAuth=()=>({userId:'superadmin-synthetic',getToken});`,
  "@/lib/api":`exports.api={
    get:async(path)=>{
      if(path.endsWith('/estado')){if(window.denied)throw Error('not authorized');return {autorizado:true,credencial_configurada:true,alcance:'directorio_sin_visitas'}}
      if(path==='/msps/')return [{msp_id:'synthetic-msp',nombre:'Proveedor de prueba'}];
      if(path.includes('/usuarios/'))return {usuario_id:'axs-owner',nombre:'Operador de prueba',email:'operator@example.test'};
      if(path.includes('/empresas/')){
        if(!window.company)throw Error('No existe');
        return {...window.company,capacidades:window.limits};
      }
      throw Error('Unsupported test route '+path);
    },
    post:async(path,body)=>{
      window.calls.push({method:'post',path,body});
      if(path.endsWith('/empresas')){
        if(!window.company)window.company={tenant_id:'corp_'+body.request_id.replaceAll('-',''),nombre:body.nombre,msp_id:body.msp_id,owner_user_id:body.owner_user_id,modalidad:'corporativo',directorio_habilitado:false,privacy_notice_version:body.privacy_notice_version,privacy_contact:body.privacy_contact};
        if(window.uncertainOnce){window.uncertainOnce=false;throw Error('Se perdió la respuesta, resultado incierto');}
        return window.company;
      }
      if(path.endsWith('/habilitar-directorio')){
        if(!window.limits)throw Error('Faltan capacidades');
        window.company.directorio_habilitado=true;return window.company;
      }
      throw Error('Unsupported POST '+path);
    },
    put:async(path,body)=>{
      window.calls.push({method:'put',path,body});
      window.limits={...body};return {tenant_id:window.company.tenant_id,...body};
    }
  };`
};
function bundle(name,parent=path.join(process.cwd(),"entry.js")){
  const f=mocks[name]?name:name.startsWith("@/")?path.join(process.cwd(),"src",name.slice(2))+".tsx":require.resolve(name,{paths:[path.dirname(parent)]});
  if(ids.has(f))return ids.get(f);
  const id=modules.length;ids.set(f,id);modules.push("");
  let s=mocks[name]||fs.readFileSync(f,"utf8");
  if(/\.tsx?$/.test(f))s=ts.transpileModule(s,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2020}}).outputText;
  s=s.replace(/require\(["']([^"']+)["']\)/g,(_,d)=>`require(${bundle(d,f)})`);
  modules[id]=`function(require,module,exports){${s}\n}`;
  return id;
}
(async()=>{
  const react=bundle("react"),reactDom=bundle("react-dom/client");
  const comp=bundle(path.join(process.cwd(),"src/components/CorporatePlatformClient.tsx"));
  const js=`const modules=[${modules.join(",")}],cache={};function require(id){if(!cache[id]){let m={exports:{}};cache[id]=m;modules[id](require,m,m.exports)}return cache[id].exports}require(${reactDom}).createRoot(document.getElementById('root')).render(require(${react}).createElement(require(${comp}).default));`;
  const css=(await require("postcss")([require("@tailwindcss/postcss")()]).process(
    fs.readFileSync("src/app/globals.css","utf8"),{from:path.resolve("src/app/globals.css")}
  )).css;
  const browser=await chromium.launch({headless:true});
  try{
    const page=await browser.newPage({viewport:{width:360,height:760}});
    await page.route("**/*",route=>route.request().url()==="http://127.0.0.1:48917/"?route.fulfill({contentType:"text/html",body:'<div id="root"></div>'}):route.abort());
    await page.goto("http://127.0.0.1:48917/");
    await page.evaluate(()=>{window.calls=[];window.company=null;window.limits=null;window.uncertainOnce=true;window.denied=false});
    await page.addStyleTag({content:css});
    await page.addScriptTag({content:js});
    const click=name=>page.getByRole("button",{name,exact:true}).click();
    await page.getByLabel("Nombre de empresa").fill("Prueba Corporativa");
    await page.getByLabel("ID del administrador AXS").fill("axs-owner");
    await click("Verificar administrador");
    await page.getByText("Usuario verificado:",{exact:false}).waitFor();
    await page.getByLabel("Contacto de privacidad").fill("privacy@example.test");
    await page.getByLabel("Versión del aviso de privacidad").fill("2026-10");
    await page.getByLabel("URL HTTPS del aviso de privacidad").fill("https://example.test/privacy");
    await click("Revisar alta de empresa");
    const region=page.getByRole("region",{name:"Confirmar operación corporativa"});
    await region.waitFor();
    assert.ok(await region.evaluate(el=>document.activeElement===el),"Confirmation receives focus");
    const beforeCancel=await page.evaluate(()=>window.calls.length);
    await click("Cancelar");
    assert.equal(await page.evaluate(()=>window.calls.length),beforeCancel);
    await click("Revisar nuevamente el mismo alta");
    await click("Confirmar operación");
    await page.getByRole("alert").waitFor();
    const first=await page.evaluate(()=>window.calls.find(c=>c.path.endsWith('/empresas')).body.request_id);
    await click("Confirmar operación");
    await page.getByText("Empresa registrada sin habilitar",{exact:false}).waitFor();
    const ids=await page.evaluate(()=>window.calls.filter(c=>c.path.endsWith('/empresas')).map(c=>c.body.request_id));
    assert.equal(ids.length,2);assert.ok(ids.every(id=>id===first),"Retry must keep UUID");

    await page.getByRole("button",{name:"Consultar empresa"}).click();
    await page.getByText("2. Configuración del directorio").waitFor();
    await click("Revisar capacidades");
    await region.waitFor();
    await click("Confirmar operación");
    await page.getByText("Solicitud de capacidades recibida",{exact:false}).waitFor();
    assert.equal(await page.getByRole("button",{name:"Revisar habilitación"}).count(),0,"No stale activation after separate GOV write");
    await click("Consultar empresa");
    await click("Revisar habilitación");
    await click("Confirmar operación");
    await page.getByText("Solicitud de habilitación recibida",{exact:false}).waitFor();
    await click("Consultar empresa");
    await page.getByText("Directorio habilitado").waitFor();

    for(const width of [320,360,1280]){
      await page.setViewportSize({width,height:760});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,"No horizontal overflow "+width);
    }
    assert.equal(await page.evaluate(()=>window.calls.filter(c=>c.path.endsWith('/habilitar-directorio')).length),1);
    console.log("PASS: responsive corporate UI, verified owner, cancelled confirmation without write, retry UUID, GOV recheck before activate, final state via API. Synthetic only.");
  }finally{await browser.close()}
})().catch(err=>{console.error(err);process.exitCode=1});
