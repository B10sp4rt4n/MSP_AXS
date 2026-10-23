const { test }=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const React=require("react");
const { renderToStaticMarkup }=require("react-dom/server");

async function renderGate({ userId="clerk-demo", token="synthetic", authorize=false, apiDown=false }={}) {
  const filename=path.resolve(__dirname,"../src/app/dashboard/corporativo/plataforma/layout.tsx");
  const source=ts.transpileModule(fs.readFileSync(filename,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}
  }).outputText;
  const requests=[];
  const module={exports:{}};
  const requireMock=name=>{
    if(name==="@clerk/nextjs/server")return{auth:async()=>({userId,getToken:async()=>token})};
    if(name==="next/navigation")return{redirect:dest=>{throw Error("redirect:"+dest)}};
    if(name==="@/lib/api")return{api:{get:async(route,bearer)=>{
      requests.push([route,bearer]);if(apiDown)throw Error("API unavailable");
      return{autorizado:authorize};
    }}};
    return require(name);
  };
  new Function("require","module","exports",source)(requireMock,module,module.exports);
  const children=React.createElement("button",null,"Crear empresa privada");
  const result=await module.exports.default({children});
  return{html:renderToStaticMarkup(result),requests};
}

test("sin sesión redirige sin consultar GOV",async()=>{
  await assert.rejects(renderGate({userId:null,authorize:true}),/redirect:\/sign-in/);
});
test("GLOBAL denegado no monta interfaz",async()=>{
  const x=await renderGate({authorize:false});
  assert.ok(!x.html.includes("Crear empresa privada"));
  assert.match(x.html,/No se puede habilitar la consola/);
  assert.deepEqual(x.requests,[["/plataforma/corporativo/estado","synthetic"]]);
});
test("sin backend o sin token falla cerrado",async()=>{
  for(const settings of [{authorize:true,apiDown:true},{authorize:true,token:null}]){
    const x=await renderGate(settings);
    assert.ok(!x.html.includes("Crear empresa privada"));
    assert.match(x.html,/No se puede habilitar la consola/);
  }
});
test("solo autoridad GLOBAL confirmada monta formulario",async()=>{
  const x=await renderGate({authorize:true});
  assert.match(x.html,/Crear empresa privada/);
});
