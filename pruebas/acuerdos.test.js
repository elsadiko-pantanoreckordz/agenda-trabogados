// Pruebas de la pestaña «Acuerdos» de la agenda.
// Lo crítico: la normalización de expedientes en la tablet debe dar el MISMO
// resultado que monitor/expedientes.py en la computadora. Ambas leen la misma
// tabla de casos, pruebas/casos_expedientes.json.
const fs = require("fs"), vm = require("vm"), path = require("path");
const RAIZ = path.resolve(__dirname, "..");
const codigo = fs.readFileSync(path.join(RAIZ, "index.html"), "utf8").match(/<script>([\s\S]*)<\/script>/)[1];

const ctx = {document:{querySelector:()=>null,querySelectorAll:()=>[],createElement:()=>({style:{},classList:{add(){},toggle(){}},addEventListener(){},appendChild(){}}),body:{appendChild(){}}},
  navigator:{}, location:{hostname:"localhost"}, indexedDB:{open:()=>({})}, console, setTimeout,
  crypto: require("crypto").webcrypto, fetch:()=>Promise.reject(new Error("sin red"))};
ctx.globalThis = ctx; ctx.window = ctx;
vm.createContext(ctx);
try { vm.runInContext(codigo + `
globalThis.__a = {expCanonico, expNormalizar, expExtraer, buscarAcuerdos, setD: v => { D = v; }};`, ctx); } catch (e) {}
const A = ctx.__a;

let fallas = 0;
const probar = (n, obtenido, esperado) => {
  const ok = JSON.stringify(obtenido) === JSON.stringify(esperado);
  console.log((ok ? "OK   " : "FALLA ") + n + ": " + JSON.stringify(obtenido) + (ok ? "" : " (se esperaba " + JSON.stringify(esperado) + ")"));
  if (!ok) fallas++;
};

// ── 1. Paridad con la computadora ──
const tabla = JSON.parse(fs.readFileSync(path.join(RAIZ, "pruebas", "casos_expedientes.json"), "utf8"));
const hoy = new Date(tabla._hoy + "T12:00:00");
let malos = 0;
for (const [entrada, canon, completo] of tabla.casos) {
  const e = A.expNormalizar(entrada, hoy);
  const obtenido = [e ? e.canonico : "", e ? e.completo : ""];
  if (obtenido[0] !== canon || obtenido[1] !== completo) {
    console.log(`FALLA ${JSON.stringify(entrada)}: ${JSON.stringify(obtenido)} (se esperaba ${JSON.stringify([canon, completo])})`);
    malos++;
  }
}
probar(`los ${tabla.casos.length} casos de la tabla compartida`, malos, 0);
probar("extrae todos sin repetir", A.expExtraer(tabla._extraccion.texto, hoy).map(x => x.completo), tabla._extraccion.esperado);

// ── 2. Búsqueda local ──
const acuerdos = [
  {uid:"1", expediente:"452/2026", expediente_crudo:"00452/2026", juzgado:"Juzgado Tercero de lo Civil de Hermosillo",
   materia:"Civil", jurisdiccion:"Estatal", partes:"JUAN PEREZ vs CONSTRUCTORA DEL NORTE",
   fecha_acuerdo:"2026-11-20", sintesis:"Se da vista por tres dias habiles", texto:"", nuevo:true},
  {uid:"2", expediente:"452/2026", expediente_crudo:"452/2026-II", juzgado:"Juzgado Tercero de lo Civil de Hermosillo",
   materia:"Civil", jurisdiccion:"Estatal", partes:"JUAN PEREZ vs CONSTRUCTORA DEL NORTE",
   fecha_acuerdo:"2026-11-18", sintesis:"Se señala audiencia de pruebas", texto:"", nuevo:false},
  {uid:"3", expediente:"1234/2026", expediente_crudo:"1234/2026", juzgado:"Juzgado Primero de Distrito",
   materia:"Amparo", jurisdiccion:"Federal", partes:"MARIA GONZALEZ vs AUTORIDADES",
   fecha_acuerdo:"2026-11-19", sintesis:"Se admite la demanda de amparo", texto:"", nuevo:true},
];
A.setD({eventos:[], expedientes:[], tribunales:[], categorias:null, meta:{}, cola:[], peticiones:[], propuestas:[],
        acuerdos, vigilados:["452/2026"]});
const vacio = {texto:"",expediente:"",juzgado:"",materia:"",jurisdiccion:"",parte:"",desde:"",hasta:"",nuevos:false,vigilados:false};
const b = f => A.buscarAcuerdos(Object.assign({}, vacio, f)).map(x => x.uid);

probar("sin filtros trae todo, más reciente primero", b({}), ["1","3","2"]);
probar("empata expediente escrito con ceros", b({expediente:"00452/2026"}), ["1","2"]);
probar("empata aunque escribas el cuaderno", b({expediente:"452/2026-II"}), ["1","2"]);
probar("busca por parte", b({parte:"constructora"}), ["1","2"]);
probar("busca por texto sin acentos", b({texto:"señala"}), ["2"]);
probar("busca por texto con acentos sobre texto sin ellos", b({texto:"senala"}), ["2"]);
probar("filtra por materia", b({materia:"amparo"}), ["3"]);
probar("filtra por fechas", b({desde:"2026-11-19"}), ["1","3"]);
probar("combina filtros", b({materia:"Civil", texto:"vista"}), ["1"]);
probar("solo nuevos", b({nuevos:true}), ["1","3"]);
probar("solo vigilados", b({vigilados:true}), ["1","2"]);
probar("varias palabras exigen todas", b({texto:"vista tres"}), ["1"]);
probar("palabra inexistente no trae nada", b({texto:"inexistente"}), []);

// El error que ya corregimos en la computadora, también aquí.
probar("buscar «*» no devuelve todo", b({texto:"*"}), []);
probar("buscar «--» no devuelve todo", b({texto:"--"}), []);
probar("buscar espacios sí devuelve todo", b({texto:"   "}), ["1","3","2"]);

process.exit(fallas ? 1 : 0);
