const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),ts=require('typescript');
async function render(userId,empresa){
 const mod={exports:{}};
 const source=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/app/dashboard/corporativo/page.tsx'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText;
 new Function('require','module','exports',source)(name=>{
  if(name==='@clerk/nextjs/server')return {auth:async()=>({userId})};
  if(name==='next/navigation')return {redirect:url=>{throw Error('redirect:'+url)}};
  if(name==='./CorporateDirectoryClient')return ()=>null;
  return require(name);
 },mod,mod.exports);
 return mod.exports.default({searchParams:Promise.resolve({empresa})});
}
test('anonymous request returns to the same company after sign-in',async()=>{
 await assert.rejects(render(null,'corp_example'),e=>e.message==='redirect:/sign-in?redirect_url='+encodeURIComponent('/dashboard/corporativo?empresa=corp_example'));
});
test('authenticated shell carries only the company selector, not inferred membership',async()=>{
 const result=await render('owner-fixture','corp_example');
 assert.deepEqual(result.props,{initialTenant:'corp_example'});
});
test('repeated company parameters do not select a company',async()=>{
 const result=await render('owner-fixture',['corp_a','corp_b']);
 assert.deepEqual(result.props,{initialTenant:''});
});
