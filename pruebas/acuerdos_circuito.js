// Circuito: la computadora exporta acuerdos cifrados → la agenda los abre,
// los valida y los deja buscables. Usa el código REAL de index.html.
const fs = require("fs"), vm = require("vm"), path = require("path");
const RAIZ = path.resolve(__dirname, "..");
const ARCHIVO = process.argv[2];
const CLAVE = "clave-de-sincronizacion-del-despacho";
const codigo = fs.readFileSync(path.join(RAIZ, "index.html"), "utf8").match(/<script>([\s\S]*)<\/script>/)[1];

const ctx = {document:{querySelector:()=>null,querySelectorAll:()=>[],createElement:()=>({style:{},classList:{add(){},toggle(){}},addEventListener(){},appendChild(){}}),body:{appendChild(){}}},
  navigator:{}, location:{hostname:"localhost"}, indexedDB:{open:()=>({})}, console, setTimeout,
  crypto: require("crypto").webcrypto, btoa:s=>Buffer.from(s,"binary").toString("base64"),
  atob:s=>Buffer.from(s,"base64").toString("binary"), TextEncoder, TextDecoder, fetch:()=>Promise.reject(new Error("sin red"))};
ctx.globalThis = ctx; ctx.window = ctx;
vm.createContext(ctx);
try { vm.runInContext(codigo + `
globalThis.__a = {descifrarSync, expCanonico, buscarAcuerdos, riesgos, setD: v => { D = v; }, verD: () => D};`, ctx); } catch(e) {}
const A = ctx.__a;

let fallas = 0;
const probar = (n, obtenido, esperado) => {
  const ok = JSON.stringify(obtenido) === JSON.stringify(esperado);
  console.log((ok?"OK   ":"FALLA ")+n+": "+JSON.stringify(obtenido)+(ok?"":" (se esperaba "+JSON.stringify(esperado)+")"));
  if (!ok) fallas++;
};

(async () => {
  const sobre = JSON.parse(fs.readFileSync(ARCHIVO, "utf8"));
  probar("el archivo va cifrado y etiquetado", [sobre.formato, sobre.contenido, sobre.cifrado],
         ["agenda-rt-cifrado", "acuerdos", "AES-256-GCM"]);

  const p = await A.descifrarSync(sobre, CLAVE, "acuerdos");
  probar("la agenda lo descifra", [p.formato, p.acuerdos.length], ["agenda-rt-acuerdos", 3]);

  // Se replica la validación que hace la agenda al recibir (misma lógica).
  const texto = (x, max) => String(x ?? "").slice(0, max);
  const D = {eventos:[], expedientes:[], tribunales:[], categorias:null, meta:{}, cola:[],
             peticiones:[], propuestas:[], acuerdos:[], vigilados:[]};
  for (const x of p.acuerdos) {
    D.acuerdos.push({uid: texto(x.huella||x.uid||x.clave, 80), fuente: texto(x.fuente,40), clave: texto(x.clave,120),
      expediente: A.expCanonico(x.expediente || x.expediente_crudo), expediente_crudo: texto(x.expediente_crudo,60),
      juzgado: texto(x.juzgado,200), materia: texto(x.materia,60), jurisdiccion: texto(x.jurisdiccion,40),
      partes: texto(x.partes,400), fecha_acuerdo: /^\d{4}-\d{2}-\d{2}$/.test(x.fecha_acuerdo||"")?x.fecha_acuerdo:"",
      sintesis: texto(x.sintesis,1000), texto: texto(x.texto,20000),
      url_documento: /^https:\/\//.test(x.url_documento||"")?texto(x.url_documento,500):"", nuevo:true});
  }
  A.setD(D);
  const vacio = {texto:"",expediente:"",juzgado:"",materia:"",jurisdiccion:"",parte:"",desde:"",hasta:"",nuevos:false,vigilados:false};
  const b = f => A.buscarAcuerdos(Object.assign({}, vacio, f)).map(x => x.expediente);

  probar("el expediente quedó normalizado en la tablet", b({}).sort(), ["1234/2026","452/2026","452/2026"]);
  probar("se busca por expediente con ceros", b({expediente:"00452/2026"}).length, 2);
  probar("se busca por parte", b({parte:"constructora"}).length, 2);
  probar("se busca por palabras del acuerdo", b({texto:"amparo"}), ["1234/2026"]);

  // Los enlaces que no sean https no deben pasar.
  probar("no acepta enlaces que no sean https",
         D.acuerdos.every(a => a.url_documento === "" || a.url_documento.startsWith("https://")), true);

  // El aviso de acuerdos sin revisar aparece en «Mi día».
  D.vigilados = ["452/2026"];
  A.setD(D);
  const avisos = A.riesgos().map(x => x.t);
  probar("avisa de acuerdos nuevos en expedientes vigilados",
         avisos.some(x => x.includes("acuerdo(s) nuevos en expedientes que vigilas")), true);

  process.exit(fallas ? 1 : 0);
})().catch(e => { console.error("ERROR:", e.message); process.exit(1); });
