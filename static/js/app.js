// Parkin Futbolero - Frontend JS con Wizard de 3 Pasos

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('registroForm');
    if (form) {
        form.addEventListener('submit', handleRegistro);
    }
});

// Estado global para datos de la factura validada
let datosFacturaGlobal = null;
let pasoActual = 1;

function mostrarCheck(id, mostrar) {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('hidden', !mostrar);
}

function ocultarTodosLosChecks() {
    ['checkNombre','checkCedula','checkTelefono','checkEmail','checkDireccion',
     'checkMarca','checkMonto','checkFecha','checkSucursal'].forEach(id => {
        mostrarCheck(id, false);
    });
}

function limpiarCampos() {
    document.getElementById('inputNombre').value = '';
    document.getElementById('inputCedula').value = '';
    document.getElementById('inputTelefono').value = '';
    document.getElementById('inputEmail').value = '';
    document.getElementById('inputDireccion').value = '';
    document.getElementById('inputFecha').value = '';
    document.getElementById('inputSucursal').value = '';
    document.getElementById('inputMarca').value = '';
    document.getElementById('checkCredito').checked = false;
    document.getElementById('checkCredito').disabled = true;
    const creditoCustom = document.getElementById('creditoUnaCustom');
    if (creditoCustom) {
        creditoCustom.classList.add('hidden');
        creditoCustom.classList.remove('bg-green-500', 'border-green-500');
    }
    document.getElementById('listaProductos').innerHTML = '';
    document.getElementById('tablaProductos').classList.add('hidden');
    document.getElementById('contadorBoletos').classList.add('hidden');
    document.getElementById('numeroBoletos').textContent = '0';
    document.getElementById('detalleBoletosTexto').textContent = '';
    ocultarTodosLosChecks();
}

// ========== WIZARD STEP NAVIGATION ==========

function actualizarIndicadorPaso(paso) {
    pasoActual = paso;

    // Paso 1
    const c1 = document.getElementById('stepCircle1');
    const l1 = document.getElementById('stepLabel1');
    const line1 = document.getElementById('stepLine1');
    if (paso >= 1) {
        c1.className = 'w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all duration-300 bg-rodelag text-white shadow-md';
        l1.className = 'text-xs font-semibold mt-1.5 transition-colors text-rodelag';
    } else {
        c1.className = 'w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all duration-300 bg-gray-200 text-gray-500';
        l1.className = 'text-xs font-semibold mt-1.5 transition-colors text-gray-400';
    }

    // Paso 2
    const c2 = document.getElementById('stepCircle2');
    const l2 = document.getElementById('stepLabel2');
    const line2 = document.getElementById('stepLine2');
    if (paso >= 2) {
        c2.className = 'w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all duration-300 bg-rodelag text-white shadow-md';
        l2.className = 'text-xs font-semibold mt-1.5 transition-colors text-rodelag';
        line1.className = 'h-full bg-rodelag transition-all duration-500 w-full';
    } else {
        c2.className = 'w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all duration-300 bg-gray-200 text-gray-500';
        l2.className = 'text-xs font-semibold mt-1.5 transition-colors text-gray-400';
        line1.className = 'h-full bg-rodelag transition-all duration-500 w-0';
    }

    // Paso 3
    const c3 = document.getElementById('stepCircle3');
    const l3 = document.getElementById('stepLabel3');
    if (paso >= 3) {
        c3.className = 'w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all duration-300 bg-rodelag text-white shadow-md';
        l3.className = 'text-xs font-semibold mt-1.5 transition-colors text-rodelag';
        line2.className = 'h-full bg-rodelag transition-all duration-500 w-full';
    } else {
        c3.className = 'w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all duration-300 bg-gray-200 text-gray-500';
        l3.className = 'text-xs font-semibold mt-1.5 transition-colors text-gray-400';
        line2.className = 'h-full bg-rodelag transition-all duration-500 w-0';
    }
}

function mostrarPaso(paso) {
    const paso1 = document.getElementById('paso1');
    const paso2 = document.getElementById('paso2');
    const paso3 = document.getElementById('paso3');

    if (paso === 1) {
        paso1.classList.remove('hidden');
        paso2.classList.add('hidden');
        paso3.classList.add('hidden');
    } else if (paso === 2) {
        paso1.classList.add('hidden');
        paso2.classList.remove('hidden');
        paso3.classList.add('hidden');
        // Scroll suave al paso 2
        paso2.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else if (paso === 3) {
        paso1.classList.add('hidden');
        paso2.classList.add('hidden');
        paso3.classList.remove('hidden');
        // Scroll suave al paso 3
        paso3.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    actualizarIndicadorPaso(paso);
}

function irAlPaso2() {
    mostrarPaso(2);
}

function irAlPaso3() {
    // Validar campos obligatorios antes de ir al paso 3
    const nombreVal = document.getElementById('inputNombre').value.trim();
    const cedulaVal = document.getElementById('inputCedula').value.trim();
    const telefono = document.getElementById('inputTelefono').value.trim();
    const email = document.getElementById('inputEmail').value.trim();
    const direccion = document.getElementById('inputDireccion').value.trim();
    const faltantes = [];
    if (!nombreVal) faltantes.push('Nombre completo');
    if (!cedulaVal) faltantes.push('Cédula / Pasaporte');
    if (!telefono) faltantes.push('Teléfono');
    if (!email) faltantes.push('Email');
    if (!direccion) faltantes.push('Dirección');

    if (faltantes.length > 0) {
        const resultado = document.getElementById('resultadoRegistro');
        resultado.classList.remove('hidden');
        resultado.className = 'mt-6 p-5 rounded-xl bg-red-50 border border-red-200 animate-fade-in';
        resultado.innerHTML = `
            <div class="flex items-start gap-3">
                <div class="text-2xl">⚠️</div>
                <div>
                    <h3 class="font-bold text-red-800">Datos incompletos</h3>
                    <p class="text-red-700 text-sm mt-1">Debes completar los siguientes campos para continuar: <strong>${faltantes.join(', ')}</strong>.</p>
                </div>
            </div>
        `;
        if (!telefono) document.getElementById('inputTelefono').focus();
        else if (!email) document.getElementById('inputEmail').focus();
        else if (!direccion) document.getElementById('inputDireccion').focus();
        return;
    }

    // Llenar resumen del paso 3
    document.getElementById('resumenFactura').textContent = datosFacturaGlobal ? (datosFacturaGlobal.id || '—') : '—';
    document.getElementById('resumenCliente').textContent = document.getElementById('inputNombre').value || '—';
    document.getElementById('resumenCedula').textContent = document.getElementById('inputCedula').value || '—';
    document.getElementById('resumenTelefono').textContent = document.getElementById('inputTelefono').value || '—';
    document.getElementById('resumenEmail').textContent = document.getElementById('inputEmail').value || '—';
    const montoElegible = datosFacturaGlobal ? parseFloat(datosFacturaGlobal.monto_elegible ?? datosFacturaGlobal.subtotal ?? 0) : 0;
    document.getElementById('resumenMonto').textContent = datosFacturaGlobal ? `B/. ${montoElegible.toFixed(2)}` : '—';
    document.getElementById('resumenBoletos').textContent = datosFacturaGlobal ? (datosFacturaGlobal.boletos_estimados || 0) : '—';
    
    const resumenCredito = document.getElementById('resumenCredito');
    if (datosFacturaGlobal && datosFacturaGlobal.credito_una) {
        resumenCredito.classList.remove('hidden');
    } else {
        resumenCredito.classList.add('hidden');
    }

    // Limpiar mensaje de error previo
    const resultado = document.getElementById('resultadoRegistro');
    resultado.classList.add('hidden');

    mostrarPaso(3);
}

// ========== VALIDACIÓN DE FACTURA ==========

async function validarFactura() {
    const numeroFactura = document.getElementById('numeroFactura').value.trim();
    const btnValidar = document.getElementById('btnValidar');
    const areaChecks = document.getElementById('areaChecks');
    const resultado = document.getElementById('resultadoRegistro');

    if (!numeroFactura) {
        await showAppModal({
            title: 'Número de factura requerido',
            message: 'Ingresa el número de factura para poder validarla.',
            confirmText: 'Entendido',
            tone: 'warning'
        });
        return;
    }

    // Resetear UI
    areaChecks.classList.remove('hidden');
    areaChecks.innerHTML = '<p class="text-sm text-gray-500">Validando factura...</p>';
    limpiarCampos();
    resultado.classList.add('hidden');
    datosFacturaGlobal = null;
    mostrarPaso(1);

    btnValidar.disabled = true;
    btnValidar.textContent = 'Validando...';

    try {
        const res = await fetch('/api/validar-factura', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({numero_factura: numeroFactura})
        });

        const json = await res.json();

        // Si hay error, mostrar solo el mensaje del check que falló
        if (!json.success) {
            areaChecks.innerHTML = '';
            json.checks.forEach(check => {
                if (!check.pass) {
                    areaChecks.innerHTML = `
                        <div class="flex items-start gap-2 px-3 py-2 rounded-lg border bg-red-50 border-red-200">
                            <span class="mt-0.5">❌</span>
                            <div class="flex-1">
                                <p class="text-sm font-semibold text-red-700">${check.campo}</p>
                                <p class="text-xs text-red-700 opacity-80">${check.mensaje}</p>
                            </div>
                        </div>
                    `;
                }
            });
            return;
        }

        // Todo pasó - ocultar área de checks
        areaChecks.classList.add('hidden');

        if (json.datos) {
            datosFacturaGlobal = json.datos;
            const cliente = json.datos.cliente;

            // Nombre: autocompletar sin bloquear edición
            const inputNombre = document.getElementById('inputNombre');
            inputNombre.value = cliente.nombre;
            mostrarCheck('checkNombre', !!cliente.nombre);

            // Cédula: autocompletar sin bloquear edición
            const inputCedula = document.getElementById('inputCedula');
            inputCedula.value = cliente.cedula;
            mostrarCheck('checkCedula', !!cliente.cedula);

            // Teléfono: autocompletar sin bloquear edición
            const inputTelefono = document.getElementById('inputTelefono');
            inputTelefono.value = cliente.telefono;
            mostrarCheck('checkTelefono', !!cliente.telefono);

            // Email: autocompletar sin bloquear edición
            const inputEmail = document.getElementById('inputEmail');
            inputEmail.value = cliente.email;
            mostrarCheck('checkEmail', !!cliente.email);

            // Dirección: autocompletar sin bloquear edición
            const inputDireccion = document.getElementById('inputDireccion');
            inputDireccion.value = cliente.direccion;
            mostrarCheck('checkDireccion', !!cliente.direccion);

            document.getElementById('inputFecha').value = json.datos.fecha;
            mostrarCheck('checkFecha', true);

            document.getElementById('inputSucursal').value = json.datos.sucursal || '';
            mostrarCheck('checkSucursal', !!json.datos.sucursal);

            // Contador de boletos
            const contador = document.getElementById('contadorBoletos');
            const numBoletos = document.getElementById('numeroBoletos');
            const detalleTexto = document.getElementById('detalleBoletosTexto');
            if (json.datos.boletos_estimados > 0) {
                contador.classList.remove('hidden');
                numBoletos.textContent = json.datos.boletos_estimados;
                const montoElegible = parseFloat(json.datos.monto_elegible ?? json.datos.subtotal ?? 0);
                const boletosBase = json.datos.boletos_base ?? json.datos.boletos_estimados;
                let texto = `B/.${montoElegible.toFixed(2)} en productos participantes = ${boletosBase} boleto(s)`;
                if (json.datos.credito_una) {
                    texto += ` · Doble por Crédito de Una = ${json.datos.boletos_estimados}`;
                }
                detalleTexto.textContent = texto;
            } else {
                contador.classList.add('hidden');
            }

            document.getElementById('inputMarca').value = json.datos.marca_principal || '';

            // Crédito de Una automático (checkbox custom verde)
            const chkCredito = document.getElementById('checkCredito');
            const creditoCustom = document.getElementById('creditoUnaCustom');
            chkCredito.checked = json.datos.credito_una;
            if (json.datos.credito_una) {
                creditoCustom.classList.remove('hidden');
                creditoCustom.classList.add('bg-green-500', 'border-green-500');
            } else {
                creditoCustom.classList.add('hidden');
                creditoCustom.classList.remove('bg-green-500', 'border-green-500');
            }

            // Tabla de productos
            const tbody = document.getElementById('listaProductos');
            tbody.innerHTML = '';
            if (json.datos.productos && json.datos.productos.length > 0) {
                json.datos.productos.forEach(prod => {
                    const desc = prod.Descripcion || 'Sin descripción';
                    const marca = prod.Marca || 'N/A';
                    const unidades = parseFloat(prod.Unidades || 0).toFixed(0);
                    const precio = parseFloat(prod.Precio_Unitario || 0).toFixed(2);
                    const aplica = prod.aplica;
                    const aplicaIcono = aplica ? '<span class="text-green-500 font-bold">✅</span>' : '<span class="text-gray-400">—</span>';
                    const aplicaClass = aplica ? 'bg-green-50' : '';
                    tbody.innerHTML += `
                        <tr class="${aplicaClass}">
                            <td class="px-3 py-2 text-gray-800">${desc}</td>
                            <td class="px-3 py-2 text-gray-600">${marca}</td>
                            <td class="px-3 py-2 text-right text-gray-700">${unidades}</td>
                            <td class="px-3 py-2 text-right text-gray-700">B/.${precio}</td>
                            <td class="px-3 py-2 text-center">${aplicaIcono}</td>
                        </tr>
                    `;
                });
                document.getElementById('tablaProductos').classList.remove('hidden');
            }

            // Ir automáticamente al paso 2 después de validar exitosamente
            mostrarPaso(2);
        }
    } catch (err) {
        areaChecks.innerHTML = `
            <div class="flex items-start gap-2 px-3 py-2 rounded-lg border bg-red-50 border-red-200">
                <span class="mt-0.5">❌</span>
                <div>
                    <p class="text-sm font-semibold text-red-700">Error de conexión</p>
                    <p class="text-xs text-red-700 opacity-80">No se pudo conectar con el servidor. Intenta de nuevo.</p>
                </div>
            </div>
        `;
        limpiarCampos();
    } finally {
        btnValidar.disabled = false;
        btnValidar.textContent = 'Validar Factura';
    }
}

// ========== REGISTRO ==========

async function handleRegistro(e) {
    e.preventDefault();
    const btn = document.getElementById('btnRegistrar');
    const resultado = document.getElementById('resultadoRegistro');

    // Validar que se haya validado la factura
    if (!datosFacturaGlobal) {
        resultado.classList.remove('hidden');
        resultado.className = 'mt-6 p-5 rounded-xl bg-red-50 border border-red-200';
        resultado.innerHTML = `
            <div class="flex items-start gap-3">
                <div class="text-2xl">⚠️</div>
                <div>
                    <h3 class="font-bold text-red-800">Error</h3>
                    <p class="text-red-700 text-sm mt-1">Primero debes validar la factura.</p>
                </div>
            </div>
        `;
        return;
    }

    const marca = datosFacturaGlobal ? datosFacturaGlobal.marca_principal : '';
    if (!marca) {
        resultado.classList.remove('hidden');
        resultado.className = 'mt-6 p-5 rounded-xl bg-red-50 border border-red-200';
        resultado.innerHTML = `
            <div class="flex items-start gap-3">
                <div class="text-2xl">⚠️</div>
                <div>
                    <h3 class="font-bold text-red-800">Error</h3>
                    <p class="text-red-700 text-sm mt-1">No se detectó marca válida en la factura.</p>
                </div>
            </div>
        `;
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Registrando...';

    // Enviar todos los datos como antes (compatibilidad con backend)
    const data = {
        numero_factura: datosFacturaGlobal.id,
        marca: marca,
        credito_una: document.getElementById('checkCredito').checked ? 1 : 0,
        nombre: document.getElementById('inputNombre').value,
        cedula: document.getElementById('inputCedula').value,
        telefono: document.getElementById('inputTelefono').value,
        email: document.getElementById('inputEmail').value,
        direccion: document.getElementById('inputDireccion').value,
        monto: datosFacturaGlobal ? datosFacturaGlobal.subtotal : 0,
        fecha_compra: document.getElementById('inputFecha').value,
        sucursal: document.getElementById('inputSucursal').value
    };

    try {
        const res = await fetch('/api/registrar', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });

        const json = await res.json();
        resultado.classList.remove('hidden');
        resultado.className = 'mt-6 p-5 rounded-xl';

        if (json.success) {
            resultado.classList.add('bg-green-50', 'border-green-200', 'border', 'animate-fade-in');

            let boletosHtml = '';
            if (json.numeros_boletos && json.numeros_boletos.length > 0) {
                boletosHtml = `
                    <div class="mt-3">
                        <p class="text-sm font-semibold text-gray-700 mb-2">Números de boletos:</p>
                        <div class="flex flex-wrap gap-2">
                            ${json.numeros_boletos.map(b => `<span class="px-3 py-1 bg-white border border-green-300 rounded-lg font-mono text-sm font-bold text-green-700">${b}</span>`).join('')}
                        </div>
                    </div>
                `;
            }

            resultado.innerHTML = `
                <div class="flex items-start gap-3">
                    <div class="text-2xl">🎉</div>
                    <div class="flex-1">
                        <h3 class="font-bold text-green-800">¡Registro exitoso!</h3>
                        <p class="text-green-700 text-sm mt-1">Has acumulado <strong>${json.boletos}</strong> boleto(s) electrónico(s).</p>
                        ${json.credito_una ? '<p class="text-xs text-yellow-700 mt-1 font-semibold">Beneficio Crédito de Una aplicado (doble boletos)</p>' : ''}
                        ${boletosHtml}
                        <p class="text-xs text-gray-500 mt-3">Guarda los números de tus boletos. Puedes consultarlos con tu cédula en cualquier momento.</p>
                    </div>
                </div>
            `;

            // Resetear formulario
            e.target.reset();
            document.getElementById('areaChecks').classList.add('hidden');
            limpiarCampos();
            datosFacturaGlobal = null;
            mostrarPaso(1);
        } else {
            resultado.classList.add('bg-red-50', 'border-red-200', 'border', 'animate-fade-in');
            resultado.innerHTML = `
                <div class="flex items-start gap-3">
                    <div class="text-2xl">⚠️</div>
                    <div>
                        <h3 class="font-bold text-red-800">Error en el registro</h3>
                        <p class="text-red-700 text-sm mt-1">${json.message}</p>
                    </div>
                </div>
            `;
        }
    } catch (err) {
        resultado.classList.remove('hidden');
        resultado.className = 'mt-6 p-5 rounded-xl bg-red-50 border border-red-200';
        resultado.innerHTML = `
            <div class="flex items-start gap-3">
                <div class="text-2xl">❌</div>
                <div>
                    <h3 class="font-bold text-red-800">Error de conexión</h3>
                    <p class="text-red-700 text-sm mt-1">No se pudo conectar con el servidor. Intenta de nuevo.</p>
                </div>
            </div>
        `;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Registrar Factura';
    }
}

// ========== CONSULTA DE BOLETOS ==========

let tipoBusquedaActual = 'cedula';

function cambiarTabConsulta(tipo) {
    tipoBusquedaActual = tipo;
    const tabCedula = document.getElementById('tabCedula');
    const tabBoleto = document.getElementById('tabBoleto');
    const tabFactura = document.getElementById('tabFactura');
    const input = document.getElementById('consultaInput');
    const resultado = document.getElementById('resultadoConsulta');

    // Resetear todos los tabs
    tabCedula.className = 'flex-1 py-2 text-sm font-semibold rounded-md transition text-gray-500 hover:text-gray-700';
    tabBoleto.className = 'flex-1 py-2 text-sm font-semibold rounded-md transition text-gray-500 hover:text-gray-700';
    tabFactura.className = 'flex-1 py-2 text-sm font-semibold rounded-md transition text-gray-500 hover:text-gray-700';

    if (tipo === 'cedula') {
        tabCedula.className = 'flex-1 py-2 text-sm font-semibold rounded-md transition bg-white text-gray-900 shadow-sm';
        input.placeholder = 'Ingresa tu cédula';
    } else if (tipo === 'boleto') {
        tabBoleto.className = 'flex-1 py-2 text-sm font-semibold rounded-md transition bg-white text-gray-900 shadow-sm';
        input.placeholder = 'Ingresa tu número de boleto';
    } else {
        tabFactura.className = 'flex-1 py-2 text-sm font-semibold rounded-md transition bg-white text-gray-900 shadow-sm';
        input.placeholder = 'Ingresa el número de factura';
    }
    resultado.classList.add('hidden');
    input.value = '';
}

async function consultarBoletos() {
    const valor = document.getElementById('consultaInput').value.trim();
    const resultado = document.getElementById('resultadoConsulta');

    if (!valor) {
        resultado.classList.remove('hidden');
        resultado.innerHTML = `<p class="text-sm text-red-600">Ingresa un valor para consultar</p>`;
        return;
    }

    resultado.classList.remove('hidden');
    resultado.innerHTML = `<p class="text-sm text-gray-500">Buscando...</p>`;

    try {
        let url;
        if (tipoBusquedaActual === 'cedula') {
            url = `/api/consultar?cedula=${encodeURIComponent(valor)}`;
        } else if (tipoBusquedaActual === 'boleto') {
            url = `/api/consultar?boleto=${encodeURIComponent(valor.toUpperCase())}`;
        } else {
            url = `/api/consultar?factura=${encodeURIComponent(valor)}`;
        }

        const res = await fetch(url);
        const json = await res.json();

        if (json.success) {
            const boletosActivos = json.boletos.filter(b => b.asignado_en_sorteo === 0);
            const boletosSorteados = json.boletos.filter(b => b.asignado_en_sorteo === 1);

            resultado.innerHTML = `
                <div class="bg-gray-50 rounded-xl p-5 border border-gray-200 animate-fade-in">
                    <div class="flex justify-between items-start mb-3">
                        <div>
                            <h4 class="font-bold text-gray-900">${json.participante.nombre}</h4>
                            <p class="text-xs text-gray-500">${json.participante.cedula}</p>
                        </div>
                        <span class="px-3 py-1 bg-rodelag/10 text-rodelag rounded-full text-xs font-bold">
                            ${json.total_boletos} boletos
                        </span>
                    </div>

                    ${boletosActivos.length > 0 ? `
                        <div class="mb-3">
                            <p class="text-xs font-semibold text-green-700 uppercase tracking-wide mb-2">Boletos activos</p>
                            <div class="flex flex-wrap gap-2">
                                ${boletosActivos.map(b => `<span class="px-2.5 py-1 bg-white border border-green-300 rounded-lg font-mono text-xs font-bold text-green-700">${b.numero_boleto}</span>`).join('')}
                            </div>
                        </div>
                    ` : ''}

                    ${boletosSorteados.length > 0 ? `
                        <div>
                            <p class="text-xs font-semibold text-gold uppercase tracking-wide mb-2">Boletos en sorteos</p>
                            <div class="flex flex-wrap gap-2">
                                ${boletosSorteados.map(b => `<span class="px-2.5 py-1 bg-yellow-50 border border-yellow-300 rounded-lg font-mono text-xs font-bold text-yellow-700">${b.numero_boleto}</span>`).join('')}
                            </div>
                        </div>
                    ` : ''}

                    ${json.participante.es_ganador ? `
                        <div class="mt-3 p-3 bg-gold/20 border border-gold/30 rounded-lg">
                            <p class="text-sm font-bold text-yellow-800">🏆 ¡Eres ganador de la promoción!</p>
                        </div>
                    ` : ''}
                </div>
            `;
        } else {
            resultado.innerHTML = `
                <div class="bg-red-50 rounded-xl p-4 border border-red-200">
                    <p class="text-sm text-red-700">${json.message}</p>
                </div>
            `;
        }
    } catch (err) {
        resultado.innerHTML = `
            <div class="bg-red-50 rounded-xl p-4 border border-red-200">
                <p class="text-sm text-red-700">Error al consultar. Intenta de nuevo.</p>
            </div>
        `;
    }
}
