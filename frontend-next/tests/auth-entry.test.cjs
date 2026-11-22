const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),ts=require('typescript');
const React=require('react'),{renderToStaticMarkup}=require('react-dom/server');
for(const [page,component] of [['sign-in','SignIn'],['sign-up','SignUp']]){
 test(page+' uses the general dashboard fallback and preserves Clerk return destinations',()=>{
  const source=ts.transpileModule(fs.readFileSync(`src/app/${page}/[[...${page}]]/page.tsx`,'utf8'),{
   compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX},
  }).outputText;
  const calls=[],module={exports:{}};
  vm.runInThisContext(`(function(require,module,exports){${source}\n})`)(name=>{
   if(name==='@/components/AxsBrand')return{__esModule:true,default:()=>null};
   if(name==='@clerk/nextjs')return{[component]:props=>{calls.push(props);return null;}};
   return require(name);
  },module,module.exports);
  renderToStaticMarkup(React.createElement(module.exports.default));
  assert.equal(calls.length,1);assert.equal(calls[0].fallbackRedirectUrl,'/dashboard');
  assert.equal(calls[0].forceRedirectUrl,undefined);
 });
}
