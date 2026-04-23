// Parkin Futbolero - Frontend JS

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('registroForm');
    if (form) {
        form.addEventListener('submit', handleRegistro);
    }
});

async function handleRegistro(e) {
    e.preventDefault();
    const btn = document.getElementById('btnRegistrar');
    const resultado = document.getElementById('resultadoRegistro');
    
    btn.disabled = true;
    btn.textContent = 'Registrando...';
    
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());
    data.credito_una = formData.has('credito_una') ? 1 : 0;
    data.monto = parseFloat(data.monto) || 0;
    
    try {
        const res = await fetch('/api/registrar', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        
        const json = await res.json();
        resultado.classList.remove('hidden', 'bg-green-50', 'bg-red-50', 'border-green-200', 'border-red-200');
        
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
                        <p class="text-xs text-gray-500 mt-3">Se ha enviado un correo de confirmación.</p>
                    </div>
                </div>
            `;
            e.target.reset();
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
        resultado.classList.add('bg-red-50', 'border-red-200', 'border', 'animate-fade-in');
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

async function consultarBoletos() {
    const cedula = document.getElementById('consultaCedula').value.trim();
    const resultado = document.getElementById('resultadoConsulta');
    
    if (!cedula) {
        resultado.classList.remove('hidden');
        resultado.innerHTML = `<p class="text-sm text-red-600">Ingresa una cédula para consultar</p>`;
        return;
    }
    
    resultado.classList.remove('hidden');
    resultado.innerHTML = `<p class="text-sm text-gray-500">Buscando...</p>`;
    
    try {
        const res = await fetch(`/api/consultar?cedula=${encodeURIComponent(cedula)}`);
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
