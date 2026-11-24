// Cifra con el código REAL de la agenda (extraído de index.html) para que Python lo abra.
const fs = require("fs"), vm = require("vm"), os = require("os");
const DIR = process.argv[2] || fs.mkdtempSync(os.tmpdir() + "/agenda-");
const codigo = fs.readFileSync("/home/user/agenda-trabogados/index.html", "utf8").match(/<script>([\s\S]*)<\/script>/)[1];
const ctx = {document:{querySelector:()=>null,querySelectorAll:()=>[],createElement:()=>({style:{},classList:{add(){},toggle(){}},addEventListener(){},appendChild(){}}),body:{appendChild(){}}},
  navigator:{}, location:{hostname:"localhost"}, indexedDB:{open:()=>({})}, console, setTimeout,
  crypto: require("crypto").webcrypto, btoa: s => Buffer.from(s,"binary").toString("base64"),
  atob: s => Buffer.from(s,"base64").toString("binary"), TextEncoder, TextDecoder, fetch: () => Promise.reject(new Error("sin red"))};
ctx.globalThis = ctx; ctx.window = ctx;
vm.createContext(ctx);
try { vm.runInContext(codigo + "\nglobalThis.__c = {cifrarSync, descifrarSync};", ctx); } catch(e) {}
const C = ctx.__c;
const clave = "clave-de-sincronizacion-del-despacho";
(async () => {
  const sobre = await C.cifrarSync({formato:"agenda-rt-peticiones", version:1, peticiones:[{uid:"p1", texto:"vista por tres días"}]}, clave, "pendientes");
  fs.writeFileSync(DIR + "/de_tablet.json", JSON.stringify(sobre));
  console.log("JS cifró pendientes (iter " + sobre.kdf.iter + ")");
  // Y abre lo que Python cifró, si ya existe.
  const ruta = DIR + "/de_pc.json";
  if (fs.existsSync(ruta)) {
    const p = await C.descifrarSync(JSON.parse(fs.readFileSync(ruta,"utf8")), clave, "propuestas");
    console.log("JS abrió lo de Python:", JSON.stringify(p).slice(0,80));
  }
})().catch(e => { console.error("ERROR:", e.message); process.exit(1); });
