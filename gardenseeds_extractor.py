#!/usr/bin/env python3
"""
GardenSeeds Pedidos Extractor
Extrae pedidos de HOY y AYER usando Playwright y los guarda en JSON para PrestaShop
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("ERROR: Playwright no está instalado")
    print("Instalar con: pip3 install playwright && playwright install chromium")
    sys.exit(1)

# Configuración - usa variables de entorno o valores por defecto
BASE_URL = "https://www.gardenseedstrading.com"
USERNAME = os.environ.get("GARDENSEEDS_USER", "EUROGROW")
PASSWORD = os.environ.get("GARDENSEEDS_PASS", "Eurogrow1234")

def log(msg):
    """Log con timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

def login(page):
    """Realizar login en GardenSeeds"""
    log("Navegando a home...")
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
    
    # Esperar a que cargue completamente
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except:
        pass
    
    log("Buscando botón de login...")
    try:
        # Intentar varias formas de abrir el modal de login
        modal_opened = False
        
        try:
            page.get_by_text("Iniciar Sesión", exact=False).first.click(timeout=4000)
            modal_opened = True
        except:
            pass
        
        if not modal_opened:
            try:
                page.locator("text=Iniciar Sesión").first.click(timeout=3000)
                modal_opened = True
            except:
                pass
        
        if not modal_opened:
            # Disparar evento Alpine.js
            page.evaluate("""
                try {
                    document.dispatchEvent(new CustomEvent('mostrarlogin'));
                    window.dispatchEvent(new CustomEvent('mostrarlogin'));
                } catch (e) {}
            """)
        
        # Esperar un momento para que se abra el modal
        page.wait_for_timeout(1000)
        
        log("Esperando formulario de login...")
        page.wait_for_selector("#iniciosesion, form#iniciosesion, input#usuario, input[name='usuario']", timeout=15000)
        
        log(f"Rellenando credenciales (usuario: {USERNAME[:3]}***)...")
        
        # Intentar rellenar usuario
        if page.locator("#usuario").count():
            page.fill("#usuario", USERNAME)
        elif page.locator("input[name='usuario']").count():
            page.fill("input[name='usuario']", USERNAME)
        else:
            page.locator("input[type='text']").first.fill(USERNAME)
        
        # Intentar rellenar password
        if page.locator("#password").count():
            page.fill("#password", PASSWORD)
        elif page.locator("input[name='password']").count():
            page.fill("input[name='password']", PASSWORD)
        else:
            page.locator("input[type='password']").first.fill(PASSWORD)
        
        log("Enviando formulario...")
        
        # Intentar hacer clic en botón submit
        clicked = False
        for sel in [
            "#iniciosesion button[type='submit']",
            "form#iniciosesion button:has-text('ACCEDER')",
            "button:has-text('ACCEDER')",
            "input[type='submit']",
            "text=ACCEDER"
        ]:
            try:
                page.click(sel, timeout=3000)
                clicked = True
                log(f"  → Clic en: {sel}")
                break
            except:
                continue
        
        if not clicked:
            try:
                page.evaluate("document.getElementById('iniciosesion').submit()")
                log("  → Submit via JS")
            except:
                page.keyboard.press("Enter")
                log("  → Submit via Enter")
        
        log("Esperando confirmación de login...")
        
        # Esperar más tiempo para la respuesta del servidor
        page.wait_for_timeout(3000)
        
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except:
            pass
        
        # Verificar que el login fue exitoso
        login_ok = False
        
        # Verificar por URL (si redirigió a cuenta)
        if "/micuenta" in page.url or "/cuenta" in page.url:
            login_ok = True
            log("  → Detectado por URL")
        
        # Verificar por elementos en la página
        if not login_ok:
            for sel in ["text=Mi cuenta", "text=Salir", "text=Cerrar sesión", "text=Pedidos", "a[href*='micuenta']"]:
                try:
                    if page.locator(sel).first.is_visible(timeout=2000):
                        login_ok = True
                        log(f"  → Detectado por: {sel}")
                        break
                except:
                    continue
        
        # Verificar que NO aparece el formulario de login (indica que se cerró)
        if not login_ok:
            try:
                if not page.locator("#iniciosesion").is_visible(timeout=1000):
                    # El modal se cerró, probablemente login exitoso
                    login_ok = True
                    log("  → Modal cerrado (asumiendo éxito)")
            except:
                pass
        
        if not login_ok:
            # Guardar screenshot para debug
            try:
                page.screenshot(path="login_failed.png")
                log("  → Screenshot guardado: login_failed.png")
            except:
                pass
            raise Exception("Login falló - no se detectó sesión iniciada")
        
        log("✓ Login exitoso")
        return True
        
    except Exception as e:
        log(f"✗ Error en login: {e}")
        return False

def get_pedidos(page, fechas):
    """Obtener pedidos de una lista de fechas"""
    log(f"Navegando a página de pedidos...")
    page.goto(f"{BASE_URL}/micuenta/pedidos", wait_until="domcontentloaded", timeout=45000)
    
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except:
        pass
    
    log("Parseando tabla de pedidos...")
    
    # Esperar a que aparezca la tabla
    try:
        page.wait_for_selector("table.fondoblanco, table", timeout=10000)
    except:
        log("✗ No se encontró tabla de pedidos")
        return []
    
    # Extraer pedidos con JavaScript
    pedidos_data = page.evaluate("""
        () => {
            const rows = document.querySelectorAll('table.fondoblanco tbody tr, table tbody tr');
            const pedidos = [];
            
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length < 2) return;
                
                const link = cells[0].querySelector('a');
                if (!link) return;
                
                const href = link.getAttribute('href');
                const numero = link.textContent.trim();
                const fecha = cells[1].textContent.trim();
                
                // Extraer ID del href
                const match = href.match(/\\/pedido\\/(\\w+)$/);
                const id = match ? match[1] : '';
                
                if (id) {
                    pedidos.push({
                        id: id,
                        numero: numero,
                        fecha: fecha,
                        href: href
                    });
                }
            });
            
            return pedidos;
        }
    """)
    
    log(f"Encontrados {len(pedidos_data)} pedidos en la página")
    
    # Convertir fechas a set para búsqueda rápida
    fechas_set = set(fechas)
    
    # Convertir fecha de dd/mm/yyyy a yyyy-mm-dd y filtrar
    pedidos_filtrados = []
    for p in pedidos_data:
        try:
            fecha_parts = p['fecha'].split('/')
            if len(fecha_parts) == 3:
                fecha_formatted = f"{fecha_parts[2]}-{fecha_parts[1]}-{fecha_parts[0]}"
                p['fecha_formatted'] = fecha_formatted
                
                # Filtrar por CUALQUIERA de las fechas objetivo
                if fecha_formatted in fechas_set:
                    pedidos_filtrados.append(p)
        except:
            continue
    
    log(f"✓ {len(pedidos_filtrados)} pedidos coinciden con fechas {fechas}")
    return pedidos_filtrados

def get_pedido_detalle(page, pedido):
    """Obtener detalle de un pedido (productos)"""
    url = f"{BASE_URL}/documentos/pedido/{pedido['id']}"
    log(f"Obteniendo detalle de pedido {pedido['numero']}...")
    
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except:
        pass
    
    # Extraer productos con JavaScript
    productos = page.evaluate("""
        () => {
            const rows = document.querySelectorAll('table tbody tr');
            const productos = [];
            
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length < 2) return;
                
                let referencia = '';
                let cantidad = 1;
                let denominacion = '';
                
                // Buscar en las primeras 4 columnas
                for (let i = 0; i < Math.min(cells.length, 4); i++) {
                    const texto = cells[i].textContent.trim();
                    
                    // Referencia: mayúsculas y números/guiones
                    if (/^[A-Z0-9\-]+$/.test(texto) && texto.length > 2 && i < 2 && !referencia) {
                        referencia = texto;
                    }
                    
                    // Cantidad: número
                    if (/^\\d+$/.test(texto) && parseInt(texto) > 0 && parseInt(texto) < 10000 && cantidad === 1) {
                        cantidad = parseInt(texto);
                    }
                    
                    // Denominación: texto largo
                    if (texto.length > 20 && !denominacion) {
                        denominacion = texto.substring(0, 100);
                    }
                }
                
                if (referencia) {
                    productos.push({
                        referencia: referencia,
                        denominacion: denominacion,
                        cantidad: cantidad
                    });
                }
            });
            
            return productos;
        }
    """)
    
    log(f"  → {len(productos)} productos extraídos")
    return productos

def main():
    parser = argparse.ArgumentParser(description='Extraer pedidos de GardenSeeds (HOY + AYER)')
    parser.add_argument('--date', type=str, help='Fecha específica en formato YYYY-MM-DD (ignora HOY+AYER)')
    parser.add_argument('--days', type=int, default=2, help='Número de días a extraer (default: 2 = hoy + ayer)')
    parser.add_argument('--output', type=str, default='gardenseeds_pedidos.json', help='Archivo JSON de salida')
    parser.add_argument('--headless', action='store_true', help='Ejecutar en modo headless')
    args = parser.parse_args()
    
    # Determinar fechas a buscar
    if args.date:
        # Fecha específica proporcionada
        fechas = [args.date]
    else:
        # Por defecto: HOY + AYER (o los últimos N días según --days)
        fechas = []
        for i in range(args.days):
            fecha = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            fechas.append(fecha)
    
    log(f"=== GardenSeeds Pedidos Extractor ===")
    log(f"Fechas objetivo: {fechas}")
    log(f"Salida: {args.output}")
    log(f"Headless: {args.headless}")
    
    result = {
        'success': False,
        'fechas': fechas,
        'timestamp': datetime.now().isoformat(),
        'pedidos': [],
        'resumen': {},
        'error': None
    }
    
    try:
        with sync_playwright() as p:
            log("Iniciando navegador...")
            browser = p.chromium.launch(
                headless=args.headless,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process"
                ]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1600, "height": 1000},
                java_script_enabled=True
            )
            
            page = context.new_page()
            
            # Login
            if not login(page):
                raise Exception("Login falló")
            
            # Obtener pedidos de TODAS las fechas
            pedidos = get_pedidos(page, fechas)
            
            if not pedidos:
                log("⚠ No se encontraron pedidos para las fechas indicadas")
                result['success'] = True
                result['pedidos'] = []
            else:
                # Obtener detalle de cada pedido
                for pedido in pedidos:
                    try:
                        productos = get_pedido_detalle(page, pedido)
                        pedido['productos'] = productos
                        result['pedidos'].append(pedido)
                    except Exception as e:
                        log(f"✗ Error obteniendo detalle de {pedido['numero']}: {e}")
                
                result['success'] = True
                
                # Generar resumen por fecha
                for fecha in fechas:
                    pedidos_fecha = [p for p in result['pedidos'] if p.get('fecha_formatted') == fecha]
                    productos_fecha = sum(len(p.get('productos', [])) for p in pedidos_fecha)
                    result['resumen'][fecha] = {
                        'pedidos': len(pedidos_fecha),
                        'productos': productos_fecha
                    }
                
                log(f"✓ Extracción completada: {len(result['pedidos'])} pedidos totales")
                for fecha, info in result['resumen'].items():
                    log(f"  → {fecha}: {info['pedidos']} pedidos, {info['productos']} productos")
            
            context.close()
            browser.close()
    
    except Exception as e:
        log(f"✗ Error: {e}")
        result['error'] = str(e)
    
    # Guardar JSON
    log(f"Guardando resultado en {args.output}...")
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    log("=== Proceso finalizado ===")
    
    return 0 if result['success'] else 1

if __name__ == '__main__':
    sys.exit(main())
