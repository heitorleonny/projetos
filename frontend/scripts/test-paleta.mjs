import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import {runInNewContext} from 'node:vm';
import ts from 'typescript';
const codigo=ts.transpileModule(readFileSync(new URL('../src/branding/tema.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const inline=new Map();
const padrao={'--color-primary-500':'#0D6EFD','--color-primary-600':'#0A58CA','--color-secondary-500':'#1E293B','--color-secondary-600':'#0F172A','--color-accent-500':'#14B8A6','--color-accent-600':'#0D9488'};
const raiz={style:{setProperty:(k,v)=>inline.set(k,v),removeProperty:k=>inline.delete(k)}};
const exports={};
runInNewContext(codigo,{exports,document:{documentElement:raiz},getComputedStyle:()=>({getPropertyValue:k=>inline.get(k)??padrao[k]??''})});
const {aplicarPaleta,corDeTexto,derivarPaleta}=exports;

test('trocar tenant ou restaurar padrão remove as três cores anteriores',()=>{
    aplicarPaleta({cor_primaria:'#008877',cor_secundaria:'#112244',cor_acento:'#AA3300'});
    assert.equal(inline.get('--color-primary-500'),'#008877'.toLowerCase());
    assert.equal(inline.get('--color-accent-500'),'#AA3300'.toLowerCase());
    aplicarPaleta({cor_primaria:null,cor_secundaria:null,cor_acento:null});
    for(const familia of ['primary','secondary','accent'])assert.equal(inline.has(`--color-${familia}-500`),false);
    assert.equal(inline.get('--color-on-primary-600'),'#FFFFFF');
});
test('cores claras e escuras preservam texto legível',()=>{
    assert.equal(corDeTexto('#FFFFFF'),'#000000');
    assert.equal(corDeTexto('#FFFF00'),'#000000');
    assert.equal(corDeTexto('#000000'),'#FFFFFF');
    aplicarPaleta({cor_primaria:'#FFFF00'});
    assert.equal(inline.get('--color-on-primary-600'),'#000000');
});
test('cores secundárias não sobrescrevem a rampa principal',()=>{
    const cores=derivarPaleta('#123456','secondary');
    assert.equal(cores['--color-primary-500'],undefined);
    assert.equal(cores['--color-secondary-500'],'#123456');
});

test('marca preta mantém tons de links legíveis nas superfícies escuras',()=>{
    const l=hex=>{const rgb=[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722;};
    const p=derivarPaleta('#000000');
    for(const tom of [200,300,400])assert.ok((l(p[`--color-primary-${tom}`])+.05)/(l('#1E293B')+.05)>=4.5);
});


test('hexadecimal aceita seis dígitos e rejeita códigos incompletos ou inválidos',()=>{
    assert.equal(exports.normalizarHex('#2563EB'),'#2563eb');
    assert.equal(exports.normalizarHex('  #Aa00fF  '),'#aa00ff');
    for(const valor of ['#12ZZ99','#123','#12345678','2563EB','',null])assert.equal(exports.normalizarHex(valor),null);
});

test('fundos azuis permanecem ao trocar paletas',()=>{
    aplicarPaleta({cor_primaria:'#16836B'});
    assert.equal(inline.has('--color-neutral-900'),false);
    aplicarPaleta({cor_secundaria:'#C65D3B'});
    assert.equal(inline.has('--color-neutral-800'),false);
    aplicarPaleta({cor_primaria:null,cor_secundaria:null,cor_acento:null});
    assert.equal(inline.has('--color-neutral-900'),false);
    assert.equal(inline.has('--color-neutral-800'),false);
});
