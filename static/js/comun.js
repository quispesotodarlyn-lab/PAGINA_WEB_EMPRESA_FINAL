/* Funciones compartidas por todas las páginas (JavaScript) */
var MES=['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Setiembre','Octubre','Noviembre','Diciembre'];
var RUTAS={Inicio:'/',Publicaciones:'/publicaciones',Clientes:'/clientes',Pedidos:'/pedidos',Materiales:'/materiales',Reportes:'/reportes','Configuración':'/configuracion'};
function $(i){return document.getElementById(i)}
function irA(k){location.href=RUTAS[k]}
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function money(n){return Number(n||0).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})}
function pad(n){return ('000'+n).slice(-4)}
function fd(s){if(!s)return '—';var p=String(s).slice(0,10).split('-');return p[2]+'/'+p[1]+'/'+p[0]}
function num(x){return parseFloat(String(x).replace(',','.'))||0}
function hoy(){var d=new Date();return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)}
function toast(s){var t=$('t');t.textContent=s;t.classList.add('show');setTimeout(function(){t.classList.remove('show')},2500)}
function api(m,u,b){return fetch(u,{method:m,headers:{'Content-Type':'application/json'},body:b?JSON.stringify(b):undefined}).then(function(r){return r.json().then(function(j){if(!r.ok)throw new Error(j.error||'Error del servidor');return j})})}
function falla(e){toast(e.message||'Sin conexión con el servidor')}
function despues(){if(window.recargar)recargar()}
function ago(ts){var m=Math.max(1,Math.round((Date.now()-ts)/6e4));return m<60?'hace '+m+' min':m<1440?'hace '+Math.round(m/60)+' horas':'hace '+Math.round(m/1440)+' días'}
// ---- ventana emergente y formularios
function showM(h,w){var b=$('mb');b.className='mb'+(w?' w':'');b.innerHTML=h;$('m').classList.add('show')}
function closeM(){$('m').classList.remove('show')}
$('m').addEventListener('mousedown',function(e){if(e.target===this)closeM()});
function form(title,F,ok,btn){var h='<h2 style="font-size:17px">'+title+'</h2><div class="fg">';
F.forEach(function(f){h+='<label'+(f.w?' style="grid-column:1/-1"':'')+'>'+f.l;var v=f.v==null?'':f.v;
if(f.t=='select')h+='<select id="f_'+f.k+'">'+f.o.map(function(o){return '<option'+(o==v?' selected':'')+'>'+esc(o)+'</option>'}).join('')+'</select>';
else if(f.t=='area')h+='<textarea id="f_'+f.k+'" rows="2">'+esc(v)+'</textarea>';
else h+='<input id="f_'+f.k+'" type="'+(f.t||'text')+'" value="'+esc(v)+'"'+(f.dl?' list="dl_'+f.k+'"':'')+(f.t=='number'?' step="any" min="0"':'')+'>'+(f.dl?'<datalist id="dl_'+f.k+'">'+f.dl.map(function(x){return '<option value="'+esc(x)+'">'}).join('')+'</datalist>':'');
h+='</label>'});
h+='</div><div class="row"><button class="x" onclick="closeM()">Cancelar</button><button id="okb">'+(btn||'Guardar')+'</button></div>';showM(h);
$('okb').onclick=function(){var v={};F.forEach(function(f){v[f.k]=$('f_'+f.k).value.trim()});ok(v).then(function(){closeM();despues()},falla)}}
function twoStep(b,fn){if(b.dataset.s){fn();return}b.dataset.s=1;var t=b.textContent;b.textContent='¿Seguro? Toca otra vez';setTimeout(function(){b.dataset.s='';b.textContent=t},3000)}
// ---- compras (un solo formulario: cliente + teléfono + material + metros + precio; la fecha es automática)
function meas(o){return o.ancho>0||o.alto>0?o.ancho+' × '+o.alto+' m':'—'}
function area(o){return Math.round(o.ancho*o.alto*100)/100}
function chip(o){return '<span class="st '+(o.estado=='C'?'ok':'p')+'" data-tog="'+o.id+'">'+(o.estado=='C'?'Completado':'En proceso')+'</span>'}
function tablaPedidos(L){if(!L.length)return '<p style="color:var(--mut);padding:14px">No se encontraron pedidos.</p>';
return '<div class="tw"><table><thead><tr><th>N°</th><th>Fecha de compra</th><th>Cliente</th><th>Teléfono</th><th>Tipo de material</th><th>Tamaño</th><th>Precio</th><th>Estado</th></tr></thead><tbody>'+L.map(function(o){return '<tr data-id="'+o.id+'"><td>#'+pad(o.id)+'</td><td>'+fd(o.fecha)+'</td><td>'+esc(o.cliente)+'</td><td>'+esc(o.telefono||'—')+'</td><td>'+esc(o.material||'—')+'</td><td>'+meas(o)+'</td><td>S/ '+money(o.precio)+'</td><td>'+chip(o)+'</td></tr>'}).join('')+'</tbody></table></div>'}
function resumen(L){return kp([['Pedidos',L.length],['Total vendido','S/ '+money(L.reduce(function(s,o){return s+o.precio},0))],['Área total',Math.round(L.reduce(function(s,o){return s+o.ancho*o.alto},0))+' m²']])}
function kp(a){return '<div class="kp">'+a.map(function(x){return '<div><b>'+x[1]+'</b><small>'+x[0]+'</small></div>'}).join('')+'</div>'}
function formVenta(id,pre){Promise.all([api('GET','/api/clientes'),api('GET','/api/materiales'),id?api('GET','/api/pedidos/'+id):Promise.resolve(null)]).then(function(r){
var C=r[0],M=r[1],o=r[2];
form(o?'Editar pedido #'+pad(o.id):'Nuevo pedido',[
{k:'cliente',l:'Nombre del cliente',dl:C.map(function(c){return c.nombre}),v:o?o.cliente:(pre||''),w:1},
{k:'telefono',l:'Teléfono',v:o?o.telefono:'',w:1},
{k:'material',l:'Tipo de material que quiere',dl:M.map(function(m){return m.nombre}),v:o?o.material:'',w:1},
{k:'ancho',l:'Metros: ancho',t:'number',v:o?o.ancho:''},{k:'alto',l:'Metros: alto',t:'number',v:o?o.alto:''},{k:'precio',l:'Precio (S/)',t:'number',v:o?o.precio:''}],function(v){
if(!v.cliente){toast('Escribe el nombre del cliente');return Promise.reject({message:'Falta el nombre'})}
return o?api('PUT','/api/pedidos/'+o.id,v).then(function(){toast('Pedido guardado')}):api('POST','/api/pedidos',v).then(function(){toast('Pedido registrado con la fecha de hoy')})},o?'Guardar cambios':'Guardar');
$('mb').querySelector('.fg').insertAdjacentHTML('afterend','<p style="color:var(--mut);font-size:12px;margin:2px 0">📅 Fecha de compra: <b>'+fd(o?o.fecha:hoy())+'</b> '+(o?'':'(se guarda automáticamente)')+'</p>');
$('f_cliente').oninput=function(){var n=this.value.trim().toLowerCase(),c=C.filter(function(x){return x.nombre.toLowerCase()==n})[0];if(c&&!$('f_telefono').value)$('f_telefono').value=c.telefono||''}},falla)}
function verPedido(id){api('GET','/api/pedidos/'+id).then(function(o){
showM('<h2 style="font-size:18px">Pedido #'+pad(o.id)+' '+chip(o)+'</h2><div class="dl">'+
[['Cliente','<a class="lk" data-cl="'+o.cliente_id+'">'+esc(o.cliente)+'</a>'],['Teléfono',esc(o.telefono||'—')],['Tipo de material',esc(o.material||'—')],['Tamaño (ancho × alto)',meas(o)],['Área',(o.ancho>0?area(o)+' m²':'—')],['Precio','<b>S/ '+money(o.precio)+'</b>'],['Fecha de compra',fd(o.fecha)],['ID del cliente',o.cliente_id]].map(function(x){return '<div><small>'+x[0]+'</small>'+x[1]+'</div>'}).join('')+
'</div><div class="row" style="margin-top:10px"><button onclick="formVenta('+o.id+')">Editar</button><button class="g" onclick="cambiarEstado('+o.id+',1)">Marcar '+(o.estado=='C'?'en proceso':'completado')+'</button><button class="d" onclick="twoStep(this,function(){borrarPedido('+o.id+')})">Eliminar</button><button class="x" onclick="closeM()">Cerrar</button></div>',1)},falla)}
function cambiarEstado(id,reabrir){api('POST','/api/pedidos/'+id+'/estado').then(function(){toast('Estado actualizado');if(reabrir)verPedido(id);despues()},falla)}
function borrarPedido(id){api('DELETE','/api/pedidos/'+id).then(function(){closeM();toast('Pedido eliminado');despues()},falla)}
// ---- clientes, materiales, publicaciones
function formCliente(id){api('GET','/api/clientes/'+id).then(function(r){var c=r.cliente;
form('Editar cliente',[{k:'nombre',l:'Nombre',v:c.nombre,w:1},{k:'telefono',l:'Teléfono',v:c.telefono,w:1}],function(v){
if(!v.nombre){toast('Escribe el nombre');return Promise.reject({message:'Falta el nombre'})}return api('PUT','/api/clientes/'+id,v).then(function(){toast('Cliente guardado')})})},falla)}
function verCliente(id){api('GET','/api/clientes/'+id).then(function(r){var c=r.cliente,L=r.pedidos;
showM('<h2 style="font-size:18px">'+esc(c.nombre)+'</h2><div class="dl"><div><small>ID</small>'+c.id+'</div><div><small>Teléfono</small>'+esc(c.telefono||'—')+'</div><div><small>Pedidos</small>'+L.length+'</div><div><small>Total comprado</small><b>S/ '+money(L.reduce(function(s,o){return s+o.precio},0))+'</b></div></div><h3 style="margin:12px 0 4px;font-size:14px">Historial de pedidos</h3>'+tablaPedidos(L)+'<div class="row" style="margin-top:8px"><button onclick="formVenta(0,\''+esc(c.nombre).replace(/'/g,'')+'\')">Nuevo pedido</button><button onclick="formCliente('+c.id+')">Editar</button><a class="btn g" href="/api/csv/cliente?id='+c.id+'">⬇ CSV</a><button class="d" onclick="twoStep(this,function(){api(\'DELETE\',\'/api/clientes/'+c.id+'\').then(function(){closeM();despues()},falla)})">Eliminar</button><button class="x" onclick="closeM()">Cerrar</button></div>',1)},falla)}
function formMaterial(){form('Nuevo material',[{k:'nombre',l:'Tipo de material (ej: Canvas)',w:1}],function(v){if(!v.nombre){toast('Escribe el nombre');return Promise.reject({message:'Falta el nombre'})}return api('POST','/api/materiales',v).then(function(){toast('Material guardado')})})}
function comprimir(f){return new Promise(function(res){if(!f)return res(null);var img=new Image();img.onload=function(){var s=Math.min(1,1400/Math.max(img.width,img.height)),c=document.createElement('canvas');c.width=img.width*s;c.height=img.height*s;var x=c.getContext('2d');x.fillStyle='#fff';x.fillRect(0,0,c.width,c.height);x.drawImage(img,0,0,c.width,c.height);c.toBlob(function(b){res(b||f)},'image/jpeg',.85)};img.onerror=function(){res(f)};img.src=URL.createObjectURL(f)})}
function verImagen(src){showM('<img src="'+src+'" alt="" style="width:100%;border-radius:10px"><div class="row" style="margin-top:8px"><button class="x" onclick="closeM()">Cerrar</button></div>',1)}
function formPub(id){(id?api('GET','/api/publicaciones').then(function(l){return l.filter(function(x){return x.id==id})[0]}):Promise.resolve({})).then(function(b){
showM('<h2 style="font-size:17px">'+(id?'Editar publicación':'Nueva publicación')+'</h2><div class="fg" style="grid-template-columns:1fr"><label>Imagen'+(id?' (déjala vacía para conservar la actual)':'')+'<input type="file" id="pi" accept="image/*"></label><img id="pv" class="pimg" alt="" style="'+(b.imagen?'':'display:none')+'" src="'+(b.imagen?'/uploads/'+esc(b.imagen):'')+'"><label>Breve descripción<textarea id="pd" rows="3" maxlength="300" placeholder="Ej: Lona publicitaria 3x2 m para evento">'+esc(b.descripcion||'')+'</textarea></label><label>Estado<select id="pe"><option'+(b.estado=='Borrador'?'':' selected')+'>Publicada</option><option'+(b.estado=='Borrador'?' selected':'')+'>Borrador</option></select></label></div><div class="row"><button class="x" onclick="closeM()">Cancelar</button><button id="okb">Guardar</button></div>');
$('pi').onchange=function(){var f=this.files[0];if(f){$('pv').src=URL.createObjectURL(f);$('pv').style.display='block'}};
$('okb').onclick=function(){var f=$('pi').files[0];if(!id&&!f){toast('Elige una imagen');return}var btn=this;btn.disabled=true;btn.textContent='Guardando...';
comprimir(f).then(function(blob){var fd=new FormData();if(blob)fd.append('imagen',blob,'foto.jpg');fd.append('descripcion',$('pd').value);fd.append('estado',$('pe').value);
return fetch(id?'/api/publicaciones/'+id:'/api/publicaciones',{method:id?'PUT':'POST',body:fd})}).then(function(r){return r.json().then(function(j){if(!r.ok)throw new Error(j.error||'Error');return j})}).then(function(){closeM();toast('Publicación guardada');despues()}).catch(function(e){btn.disabled=false;btn.textContent='Guardar';falla(e)})}},falla)}
function verActividades(){api('GET','/api/actividades?limite=20').then(function(L){showM('<h2 style="font-size:17px">Actividades</h2>'+L.map(function(a){return '<div class="act"><div class="i" style="background:'+a.col+'">'+a.i+'</div><div>'+esc(a.t)+'<small>'+esc(a.s)+' • '+ago(a.ts)+'</small></div></div>'}).join('')+'<div class="row"><button class="x" onclick="closeM()">Cerrar</button></div>')},falla)}
// ---- gráficos
function nice(v){var p=Math.pow(10,Math.floor(Math.log(v||1)/Math.LN10)),m=[1,2,2.5,5,10];for(var i=0;i<5;i++)if(m[i]*p>=v)return m[i]*p;return 10*p}
function sh(v){return v>=1000?(v/1000).toFixed(1)+'k':Math.round(v)}
function bars(a){var mx=a.reduce(function(m,x){return Math.max(m,x.v)},0),M=nice(mx/4)*4||4,s='<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff2fa8"/><stop offset="1" stop-color="#1a8cff"/></linearGradient></defs>',n=a.length,w=560/n,i;
for(i=0;i<=4;i++){var y=190-i*.25*170;s+='<line x1="50" x2="620" y1="'+y+'" y2="'+y+'" stroke="#1b2a52"/><text x="44" y="'+(y+3)+'" fill="#9fb0d6" font-size="9" text-anchor="end">'+sh(M*i/4)+'</text>'}
a.forEach(function(d,i){var h=d.v/M*170,x=55+i*w+w*.15;s+='<rect x="'+x+'" y="'+(190-h)+'" width="'+w*.7+'" height="'+h+'" rx="4" fill="url(#bg)"/>'+(d.v?'<text x="'+(x+w*.35)+'" y="'+(186-h)+'" fill="#fff" font-size="9" text-anchor="middle">'+sh(d.v)+'</text>':'')+'<text x="'+(x+w*.35)+'" y="206" fill="#9fb0d6" font-size="10" text-anchor="middle">'+d.l+'</text>'});
return '<svg viewBox="0 0 640 215" style="width:100%">'+s+'</svg>'}
// ---- clics globales: estado, cliente, pedido
document.addEventListener('click',function(e){var t=e.target.closest('[data-tog],[data-cl],tr[data-id]');if(!t)return;if(t.dataset.tog)cambiarEstado(+t.dataset.tog);else if(t.dataset.cl){closeM();verCliente(+t.dataset.cl)}else verPedido(+t.dataset.id)});
