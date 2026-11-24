// Circuito (f): el monitor convierte acuerdos en propuestas → la agenda REAL
// las descifra y las valida como eventos antes de que puedas aprobarlas.
const fs = require("fs"), vm = require("vm"), path = require("path");
const RAIZ = path.resolve(__dirname, "..");
const ARCHIVO = process.argv[2], CLAVE = "clave-de-sincronizacion-del-despacho";
const codigo = fs.readFileSync(path.join(RAIZ, "index.html"), "utf8").match(/<script>([\s\S]*)<\/script>/)[1];

const ctx = {document:{querySelector:()=>null,querySelectorAll:()=>[],createElement:()=>({style:{},classList:{add(){},toggle(){}},addEventListener(){},appendChild(){}}),body:{appendChild(){}}},
  navigator:{}, location:{hostname:"localhost"}, indexedDB:{open:()=>({})}, console, setTimeout,
  crypto: require("crypto").webcrypto, btoa:s=>Buffer.from(s,"binary").toString("base64"),
  atob:s=>Buffer.from(s,"base64").toString("binary"), TextEncoder, TextDecoder, fetch:()=>Promise.reject(new Error("sin red"))};
ctx.globalThis = ctx; ctx.window = ctx;
vm.createContext(ctx);
try { vm.runInContext(codigo + `
globalThis.__a = {descifrarSync, eventoDePropuesta, setD: v => { D = v; }};`, ctx); } catch(e) {}
const A = ctx.__a;

A.setD({eventos:[], expedientes:[{id:9,num_expediente:"452",ano:"2026",actor:"JUAN PEREZ",demandada:"CONSTRUCTORA",juzgado:"Juzgado Tercero"}],
  tribunales:[], meta:{}, cola:[], peticiones:[], propuestas:[], acuerdos:[], vigilados:[],
  categorias:{categorias:{"Asunto del despacho":["Tarea","Audiencia","Diligencia","Vencimiento","Vigilancia","Promoción / escrito","Cita con cliente","Revisión de expediente","Otro"],
    "Personal / otro":["Reunión","Cita","Recordatorio","Pago o trámite","Llamada","Personal","Otro"]},
    requiere:["Audiencia","Diligencia","Promoción / escrito","Revisión de expediente","Vencimiento","Vigilancia"], defecto:{}}});

let fallas = 0;
const probar = (n, obtenido, esperado) => {
  const ok = JSON.stringify(obtenido) === JSON.stringify(esperado);
  console.log((ok?"OK   ":"FALLA ")+n+": "+JSON.stringify(obtenido)+(ok?"":" (se esperaba "+JSON.stringify(esperado)+")"));
  if (!ok) fallas++;
};

(async () => {
  const p = await A.descifrarSync(JSON.parse(fs.readFileSync(ARCHIVO, "utf8")), CLAVE, "propuestas");
  probar("la agenda descifra las propuestas del monitor", p.formato, "agenda-rt-propuestas");
  probar("llegaron las dos propuestas", p.propuestas.length, 2);

  const venc = p.propuestas.find(x => x.evento.tipo === "Vencimiento");
  const ev = A.eventoDePropuesta(venc);
  probar("el vencimiento pasa la validación de la agenda",
         [ev.tipo, ev.fecha, ev.expediente_id], ["Vencimiento", "2026-11-25", 9]);
  probar("amarró el expediente del despacho por número", ev.expediente_id, 9);
  probar("trae recordatorio de un día", ev.recordatorios, [1440]);
  probar("el conteo viaja completo", venc.conteo.length >= 5, true);

  const aud = p.propuestas.find(x => x.evento.tipo === "Audiencia");
  const ev2 = A.eventoDePropuesta(aud);
  probar("la audiencia pasa la validación", [ev2.fecha, ev2.hora], ["2026-12-10", "09:30"]);

  // Toda propuesta debe avisar que es propuesta.
  probar("todas se presentan como propuesta por revisar",
         p.propuestas.every(x => /revísala antes de aprobar/i.test(x.explicacion)), true);

  // Y la agenda sigue rechazando lo que no cuadra, venga de donde venga.
  let rechazado = false;
  try { A.eventoDePropuesta({...venc, evento: {...venc.evento, tipo: "Transferir fondos"}}); }
  catch (e) { rechazado = true; }
  probar("rechaza un tipo que no existe en tus categorías", rechazado, true);

  process.exit(fallas ? 1 : 0);
})().catch(e => { console.error("ERROR:", e.message); process.exit(1); });
