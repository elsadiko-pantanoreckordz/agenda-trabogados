// Usa el código REAL de la agenda para descifrar el archivo del asistente y
// validar la propuesta igual que cuando el abogado toca «Aprobar».
const fs = require("fs"), vm = require("vm");
const codigo = fs.readFileSync("/home/user/agenda-trabogados/index.html", "utf8").match(/<script>([\s\S]*)<\/script>/)[1];
const ctx = {document:{querySelector:()=>null,querySelectorAll:()=>[],createElement:()=>({style:{},classList:{add(){},toggle(){}},addEventListener(){},appendChild(){}}),body:{appendChild(){}}},
  navigator:{}, location:{hostname:"localhost"}, indexedDB:{open:()=>({})}, console, setTimeout,
  crypto: require("crypto").webcrypto, btoa: s=>Buffer.from(s,"binary").toString("base64"),
  atob: s=>Buffer.from(s,"base64").toString("binary"), TextEncoder, TextDecoder, fetch:()=>Promise.reject(new Error("sin red"))};
ctx.globalThis = ctx; ctx.window = ctx;
vm.createContext(ctx);
try { vm.runInContext(codigo + `
globalThis.__a = {descifrarSync, eventoDePropuesta, setD: v => { D = v; }, numExp};`, ctx); } catch(e) {}
const A = ctx.__a;

A.setD({eventos:[], expedientes:[{id:7,num_expediente:"452",ano:"2026",actor:"A",demandada:"B",juzgado:"Juzgado X"}],
  tribunales:[], meta:{}, cola:[], peticiones:[], propuestas:[],
  categorias:{categorias:{"Asunto del despacho":["Tarea","Audiencia","Diligencia","Vencimiento","Vigilancia","Promoción / escrito","Cita con cliente","Revisión de expediente","Otro"],
    "Personal / otro":["Reunión","Cita","Recordatorio","Pago o trámite","Llamada","Personal","Otro"]},
    requiere:["Audiencia","Diligencia","Promoción / escrito","Revisión de expediente","Vencimiento","Vigilancia"], defecto:{}}});

(async () => {
  const sobre = JSON.parse(fs.readFileSync(process.argv[2] + "/propuestas.json", "utf8"));
  const p = await A.descifrarSync(sobre, "clave-de-sincronizacion-del-despacho", "propuestas");
  console.log("OK   la agenda descifró el archivo del asistente:", p.propuestas.length, "propuesta(s)");
  let fallas = 0;
  const probar = (n, ok, extra) => { console.log((ok?"OK   ":"FALLA ") + n + (extra?": "+extra:"")); if(!ok) fallas++; };

  // La propuesta del plazo trae expediente 452/2026, que SÍ existe localmente.
  const plazo = p.propuestas.find(x => x.evento.tipo === "Vencimiento");
  const ev = A.eventoDePropuesta(plazo);
  probar("la propuesta de plazo pasa la validación", ev.fecha === "2026-11-27" && ev.tipo === "Vencimiento", JSON.stringify({fecha:ev.fecha, exp:ev.expediente_id}));
  probar("amarró el expediente local por número", ev.expediente_id === 7, String(ev.expediente_id));
  probar("puso recordatorio de un día", JSON.stringify(ev.recordatorios) === "[1440]", JSON.stringify(ev.recordatorios));

  // Propuestas manipuladas deben rebotar.
  const casos = [
    ["tipo inventado", {...plazo, evento:{...plazo.evento, tipo:"Ejecutar transferencia"}}],
    ["fecha basura", {...plazo, evento:{...plazo.evento, fecha:"mañana"}}],
    ["sin evento", {...plazo, evento:null}],
  ];
  for (const [nombre, caso] of casos) {
    let rechazado = false;
    try { A.eventoDePropuesta(caso); } catch(e) { rechazado = true; }
    probar("rechaza " + nombre, rechazado);
  }
  // Un título larguísimo se recorta en lugar de pasar entero.
  const largo = A.eventoDePropuesta({...plazo, evento:{...plazo.evento, titulo:"x".repeat(5000)}});
  probar("recorta títulos desmedidos", largo.titulo.length === 200, String(largo.titulo.length));
  process.exit(fallas ? 1 : 0);
})().catch(e => { console.error("ERROR:", e.message); process.exit(1); });
