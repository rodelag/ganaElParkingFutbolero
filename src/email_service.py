import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.config import SMTP_HOST, SMTP_PORT, SMTP_FROM, EMAIL_PRUEBAS
from src.database import obtener_config


def _modo_pruebas_activo():
    """Lee el modo de pruebas desde la base de datos."""
    return obtener_config('modo_pruebas_email', '1') == '1'


def _aplicar_modo_pruebas(destinatario):
    """
    Aplica la regla del modo de pruebas.
    Si está activo, redirige el correo a EMAIL_PRUEBAS.
    Retorna (to_email, es_modo_pruebas).
    """
    activo = _modo_pruebas_activo()
    if activo:
        return EMAIL_PRUEBAS, True
    return destinatario, False


def enviar_correo(destinatario, asunto, cuerpo_html, cuerpo_texto=None):
    """
    Función base para enviar cualquier correo.
    Aplica automáticamente la regla del modo de pruebas.
    """
    to_email, modo_pruebas = _aplicar_modo_pruebas(destinatario)

    # Agregar banner de modo de pruebas al HTML si aplica
    if modo_pruebas and cuerpo_html:
        banner = '''
        <div style="margin:16px 0;padding:12px;background:#fef3c7;border:1px solid #fbbf24;border-radius:8px;color:#92400e;font-weight:bold;text-align:center;">
            ⚠️ MODO DE PRUEBAS — Este correo fue redirigido a modo de prueba
        </div>
        '''
        # Insertar antes de cerrar </body> si existe, o al final
        if '</body>' in cuerpo_html:
            cuerpo_html = cuerpo_html.replace('</body>', banner + '</body>')
        else:
            cuerpo_html += banner

    msg = MIMEMultipart('alternative')
    msg['Subject'] = asunto
    msg['From'] = SMTP_FROM
    msg['To'] = to_email

    if cuerpo_texto:
        msg.attach(MIMEText(cuerpo_texto, 'plain', 'utf-8'))
    msg.attach(MIMEText(cuerpo_html, 'html', 'utf-8'))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.sendmail(SMTP_FROM, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f'[EMAIL ERROR] No se pudo enviar correo: {e}')
        return False


def enviar_correo_confirmacion(destinatario, nombre, numero_factura, boletos, numeros_boletos, credito_una=False):
    """
    Envía correo de confirmación al registrar una factura.
    La regla del modo de pruebas se aplica automáticamente en enviar_correo().
    """
    asunto = '🎉 Confirmación de Registro - Parkin Futbolero Rodelag'

    boletos_html = ''.join([
        f'<span style="display:inline-block;padding:8px 16px;margin:4px;background:#f0fdf4;border:1px solid #86efac;border-radius:8px;font-family:monospace;font-weight:bold;color:#166534;">{b}</span>'
        for b in numeros_boletos
    ])

    credito_html = '<p style="color:#b45309;font-weight:bold;">✨ Beneficio Crédito de Una aplicado (doble boletos)</p>' if credito_una else ''

    cuerpo = f"""
    <html>
    <body style="font-family:Arial,sans-serif;background:#f9fafb;padding:20px;">
        <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:16px;padding:32px;box-shadow:0 4px 6px rgba(0,0,0,0.1);">
            <div style="text-align:center;margin-bottom:24px;">
                <h1 style="color:#1B3A5C;margin:0;">🏆 Parkin Futbolero</h1>
                <p style="color:#666;margin:4px 0 0;">Promoción Rodelag 2026</p>
            </div>
            
            <h2 style="color:#22c55e;">¡Registro Exitoso!</h2>
            <p>Hola <strong>{nombre}</strong>,</p>
            <p>Tu factura <strong>{numero_factura}</strong> ha sido registrada correctamente en la promoción.</p>
            
            <div style="background:#f8fafc;border-radius:12px;padding:20px;margin:20px 0;">
                <p style="margin:0 0 8px;color:#475569;">Boletos acumulados: <strong style="color:#1B3A5C;font-size:24px;">{boletos}</strong></p>
                {credito_html}
            </div>
            
            <p style="color:#475569;">Tus números de boleto:</p>
            <div style="margin:12px 0;">
                {boletos_html}
            </div>
            
            <div style="margin-top:24px;padding-top:20px;border-top:1px solid #e2e8f0;color:#64748b;font-size:12px;">
                <p>Guarda estos números. Puedes consultarlos en cualquier momento ingresando tu cédula en <a href="https://parkinfutbolero.rodelag.com" style="color:#1B3A5C;">parkinfutbolero.rodelag.com</a></p>
                <p style="margin-top:12px;">Promoción válida del 30 de abril al 30 de junio de 2026.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return enviar_correo(destinatario, asunto, cuerpo)
