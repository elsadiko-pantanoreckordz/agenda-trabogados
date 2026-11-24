const fs = require("fs"), vm = require("vm");
const html = fs.readFileSync("/home/user/agenda-trabogados/index.html", "utf8");
const codigo = html.match(/<script>([\s\S]*)<\/script>/)[1];

const ctx = {
  document: {querySelector: () => null, querySelectorAll: () => [], createElement: () => ({style:{}, classList:{add(){},toggle(){}}, addEventListener(){}, appendChild(){}}), body: {appendChild(){}}},
  navigator: {}, window: {}, location: {hostname: "localhost", origin: "x"},
  indexedDB: {open: () => ({})}, console, setTimeout, clearTimeout, crypto: require("crypto").webcrypto,
  fetch: () => Promise.reject(new Error("sin red")),
};
ctx.globalThis = ctx; ctx.self = ctx;
vm.createContext(ctx);
try { vm.runInContext(codigo + "\nglobalThis.__t = {iso, riesgos, setD: v => { D = v; }};", ctx); }
catch (e) { /* el arranque necesita navegador; las funciones ya quedaron definidas */ }
const T = ctx.__t;

const hoy = new Date(), iso = d => T.iso(d);
const dia = n => { const d = new Date(hoy); d.setDate(d.getDate() + n); return iso(d); };

const datos = {
  eventos: [
    // se enciman: audiencia de 2 h a las 9:00 contra otra a las 10:00
    {uid:"a", tipo:"Audiencia", titulo:"Audiencia de pruebas", fecha:dia(2), hora:"09:00", estatus:"Pendiente", juzgado:"Juzgado Primero Mixto de Primera Instancia del Distrito Judicial de Álamos", expediente_id:1},
    {uid:"b", tipo:"Audiencia", titulo:"Audiencia conciliatoria", fecha:dia(2), hora:"10:00", estatus:"Pendiente", juzgado:"Juzgado 1o de Primera Inst. de lo Civil del Distrito Judicial de Hermosillo", expediente_id:2},
    // vencimiento en 2 días sin promoción capturada
    {uid:"c", tipo:"Vencimiento", titulo:"Vence contestación", fecha:dia(2), estatus:"Pendiente", expediente_id:3},
    // expediente 4 sin movimiento (su único evento fue hace 200 días)
    {uid:"d", tipo:"Tarea", titulo:"Vieja", fecha:dia(-200), estatus:"Completado", expediente_id:4},
  ],
  expedientes: [{id:1,num_expediente:"100",ano:"2026"},{id:2,num_expediente:"200",ano:"2026"},
                {id:3,num_expediente:"300",ano:"2026"},{id:4,num_expediente:"400",ano:"2026"}],
  tribunales: JSON.parse(fs.readFileSync("/home/user/agenda-trabogados/tribunales.json","utf8")),
  categorias: null, meta: {}, cola: [],
};
T.setD(datos);

const r = T.riesgos();
console.log("avisos obtenidos:", r.length);
r.forEach(x => console.log(`  [nivel ${x.n}] ${x.t}`));

const esperado = [
  ["se encima", "choque de horario"],
  ["Álamos y Hermosillo", "distritos distintos"],
  ["no hay promoción capturada", "vencimiento sin promoción"],
  ["sin movimiento en 60 días", "expediente olvidado"],
];
let fallas = 0;
for (const [frag, nombre] of esperado) {
  const ok = r.some(x => x.t.includes(frag));
  console.log(ok ? `OK   ${nombre}` : `FALLA ${nombre} (no apareció «${frag}»)`);
  if (!ok) fallas++;
}

// Sin respaldo nunca hecho: tiene que avisar, porque es lo único que salva los
// datos si se desinstala la app o se pierde la tablet.
const probar = (nombre, ok) => { console.log(ok ? `OK   ${nombre}` : `FALLA ${nombre}`); if (!ok) fallas++; };
probar("avisa que nunca se ha respaldado", r.some(x => x.t.includes("Nunca has hecho un respaldo")));

const hace = n => { const d = new Date(); d.setDate(d.getDate() - n); return d.toISOString(); };

// Caso negativo: agenda tranquila y con respaldo reciente no debe generar avisos.
datos.eventos = [{uid:"z", tipo:"Audiencia", titulo:"Única", fecha:dia(5), hora:"09:00", estatus:"Pendiente", juzgado:"", expediente_id:1}];
datos.expedientes = [{id:1,num_expediente:"100",ano:"2026"}];
datos.meta = {ultimo_respaldo: hace(2)};
T.setD(datos);
const r2 = T.riesgos().filter(x => x.n >= 1);
console.log(r2.length === 0 ? "OK   agenda tranquila sin avisos" : `FALLA agenda tranquila generó: ${JSON.stringify(r2)}`);
if (r2.length) fallas++;

// Respaldo viejo: avisa a partir de los 7 días, y dice cuántos han pasado.
datos.meta = {ultimo_respaldo: hace(8)};
T.setD(datos);
const viejo = T.riesgos().find(x => x.t.includes("último respaldo"));
probar("avisa cuando el respaldo tiene 8 días", !!viejo && viejo.t.includes("8 días"));

datos.meta = {ultimo_respaldo: hace(6)};
T.setD(datos);
probar("a los 6 días todavía no molesta", !T.riesgos().some(x => x.t.includes("último respaldo")));

// Una agenda vacía no tiene nada que respaldar: no debe regañar al recién llegado.
datos.eventos = []; datos.expedientes = []; datos.meta = {};
T.setD(datos);
probar("no pide respaldo si no hay nada que respaldar",
       !T.riesgos().some(x => x.t.toLowerCase().includes("respaldo")));

process.exit(fallas ? 1 : 0);
