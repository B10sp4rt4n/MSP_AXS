import fs from 'node:fs/promises';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';
await fs.mkdir('/tmp/axs-template', {recursive:true});
const w=Workbook.create();
const s=w.worksheets.add('Residentes');
s.getRange('A1:D1').values=[['vivienda','tipo','nombre','correo']];
s.getRange('A1:D1').format={fill:'#183153',font:{bold:true,color:'#FFFFFF',name:'Arial',size:11}};
s.getRange('A2:D501').setNumberFormat('@');
s.getRange('A:D').format.columnWidth=26;
s.getRange('C:D').format.columnWidth=38;
s.freezePanes.freezeRows(1);
const n=w.worksheets.add('Instrucciones');
const lines=[['AXS — Alta de residentes'],['Llena la hoja Residentes desde la fila 2. Máximo 500 residentes.'],['vivienda: identificador completo, por ejemplo Torre A-001.'],['tipo: casa, depto o local.'],['nombre: nombre completo del residente.'],['correo: correo con el que se registrará en AXS.'],['Una fila por vivienda y un residente por fila.'],['No agregues columnas, fórmulas ni datos de otro condominio.'],['Las viviendas nuevas se crean al confirmar el lote.'],['Los registros existentes no se sobrescriben.'],['El archivo no envía invitaciones ni crea cuentas en Clerk.'],['Conserva los ceros iniciales de la vivienda como texto.'],['Ejemplo (no se importa desde esta hoja):'],['Torre A-001 / depto / Ana Ejemplo / ana@example.com']];
n.getRange(`A1:A${lines.length}`).values=lines;
n.getRange('A1:A14').format.font={name:'Arial',size:11};
n.getRange('A1').format.font={bold:true,size:15};n.getRange('A:A').format.columnWidth=100;
w.recalculate();
console.log((await w.inspect({kind:'table',range:'Residentes!A1:D3',include:'values',tableMaxRows:3,tableMaxCols:4})).ndjson);
for(const [name,range] of [['Residentes','A1:D6'],['Instrucciones','A1:A14']]) {
 const b=await w.render({sheetName:name,range,scale:1.5});await fs.writeFile(`/tmp/axs-template/${name}.png`,new Uint8Array(await b.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(w)).save('backend/static/plantilla_residentes.xlsx');
