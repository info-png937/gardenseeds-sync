#!/usr/bin/env python3
"""
GardenSeeds Pedidos Extractor para GitHub Actions
Extrae pedidos usando Playwright y los guarda en JSON
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("ERROR: Playwright no está instalado")
    print("Ejecutar: pip install playwright && playwright install chromium")
    sys.exit(1)

# Configuración desde variables de entorno o argumentos
BASE_URL = "https://www.gardenseedstrading.com"
USERNAME = os.getenv('GARDENSEEDS_USER', 'EUROGROW')
PASSWORD = os.getenv('GARDENSEEDS_PASS', 'Eurogrow1234')

def log(msg):
    """Log con timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

def login(page):
    """Realizar login en GardenSeeds"""
    log("🔐 Iniciando login...")
    
    try:
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
        log("✓ Página cargada")
        
        # Hacer clic en "Iniciar Sesión"
        try:
            page.get_by_text("Iniciar Sesión", exact=False).first.click(timeout=5000)
            page.wait_for_timeout(1000)
        except:
            log("⚠ No se encontró botón 'Iniciar Sesión', probando alternativas...")
            page.evaluate("document.dispatchEvent(new CustomEvent('mostrarlogin'));")
            page.wait_for_timeout(1000)
        
        # Esperar formulario
        page.wait_for_selector("#iniciosesion, form#iniciosesion", timeout=15000)
        log("✓ Formulario de login encontrado")
        
        # Rellenar credenciales
        page.fill("#usuario, input[name='usuario']", USERNAME)
        page.fill("#password, input[name='password']", PASSWORD)
        log("✓ Credenciales rellenadas")
        
        # Submit y esperar navegación
        with page.expect_navigation(timeout=30000, wait_until="domcontentloaded"):
            try:
                page.click("#iniciosesion button[type='submit']", timeout=3000)
            except:
                page.evaluate("document.getElementById('iniciosesion').submit()")
        
        log("✓ Formulario enviado, esperando respuesta...")
        
        # Esperar a que cargue completamente
        page.wait_for_timeout(3000)
        
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except:
            pass
        
        # Verificar login de forma más robusta
        page_content = page.content()
        
        # Buscar indicadores de sesión iniciada
        if ("Salir" in page_content or 
            "salir" in page_content.lower() or 
            "Mi cuenta" in page_content or
            "Cerrar sesión" in page_content):
            log("✅ Login exitoso (detectado: Salir/Mi cuenta)")
            return True
        
        # Si NO encuentra el formulario de login, probablemente está logueado
        try:
            page.wait_for_selector("#iniciosesion", timeout=2000)
            log("❌ Todavía en página de login")
            return False
        except:
            log("✅ Login exitoso (formulario ya no visible)")
            return True
            
    except Exception as e:
        log(f"❌ Error en login: {e}")
        return False
def get_pedidos(page, fecha):
    """Obtener pedidos de una fecha específica"""
    log(f"📋 Navegando a página de pedidos...")
    
    page.goto(f"{BASE_URL}/micuenta/pedidos", wait_until="domcontentloaded", timeout=45000)
    
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except:
        pass
    
    log("🔍 Parseando tabla de pedidos...")
    
    # Esperar tabla
    try:
        page.wait_for_selector("table.fondoblanco", timeout=10000)
    except:
        log("⚠ No se encontró tabla de pedidos")
        return []
    
    # Extraer pedidos con JavaScript
    pedidos_data = page.evaluate("""
        () => {
            const rows = document.querySelectorAll('table.fondoblanco tbody tr');
            const pedidos = [];
            
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length < 2) return;
                
                const link = cells[0].querySelector('a');
                if (!link) return;
                
                const href = link.getAttribute('href');
                const numero = link.textContent.trim();
                const fecha = cells[1].textContent.trim();
                
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
    
    log(f"📦 Encontrados {len(pedidos_data)} pedidos totales")
    
    # Filtrar por fecha
    pedidos_filtrados = []
    for p in pedidos_data:
        try:
            fecha_parts = p['fecha'].split('/')
            if len(fecha_parts) == 3:
                fecha_formatted = f"{fecha_parts[2]}-{fecha_parts[1]}-{fecha_parts[0]}"
                p['fecha_formatted'] = fecha_formatted
                
                if fecha_formatted == fecha:
                    pedidos_filtrados.append(p)
        except:
            continue
    
    log(f"✅ {len(pedidos_filtrados)} pedidos coinciden con fecha {fecha}")
    return pedidos_filtrados

def get_pedido_detalle(page, pedido):
    """Obtener detalle de un pedido"""
    url = f"{BASE_URL}/documentos/pedido/{pedido['id']}"
    log(f"📄 Obteniendo detalle: {pedido['numero']}...")
    
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except:
        pass
    
    # Extraer productos
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
                
                for (let i = 0; i < Math.min(cells.length, 6); i++) {
                    const texto = cells[i].textContent.trim();
                    
                    if (/^[A-Z0-9\\-]+$/.test(texto) && texto.length > 2 && i < 2 && !referencia) {
                        referencia = texto;
                    }
                    
                    if (/^\\d+$/.test(texto) && parseInt(texto) > 0 && parseInt(texto) < 10000 && cantidad === 1) {
                        cantidad = parseInt(texto);
                    }
                    
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
    parser = argparse.ArgumentParser(description='Extraer pedidos de GardenSeeds')
    parser.add_argument('--date', type=str, help='Fecha (YYYY-MM-DD, default: ayer)')
    parser.add_argument('--output', type=str, default='pedidos_latest.json', help='Archivo JSON salida')
    parser.add_argument('--headless', action='store_true', default=True, help='Modo headless')
    args = parser.parse_args()
    
    # Fecha
    if args.date:
        fecha = args.date
    else:
        fecha = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    log("=" * 60)
    log("🌱 GardenSeeds Pedidos Extractor - GitHub Actions")
    log("=" * 60)
    log(f"📅 Fecha objetivo: {fecha}")
    log(f"💾 Salida: {args.output}")
    log(f"👤 Usuario: {USERNAME}")
    
    result = {
        'success': False,
        'fecha': fecha,
        'timestamp': datetime.now().isoformat(),
        'pedidos': [],
        'error': None,
        'stats': {
            'total_pedidos': 0,
            'total_productos': 0
        }
    }
    
    try:
        with sync_playwright() as p:
            log("🚀 Iniciando navegador Chromium...")
            browser = p.chromium.launch(
                headless=args.headless,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled"
                ]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            
            page = context.new_page()
            
            # Login
            if not login(page):
                raise Exception("Login falló")
            
            # Obtener pedidos
            pedidos = get_pedidos(page, fecha)
            
            if not pedidos:
                log("⚠ No se encontraron pedidos para la fecha indicada")
                result['success'] = True
                result['pedidos'] = []
            else:
                # Detalle de cada pedido
                for pedido in pedidos:
                    try:
                        productos = get_pedido_detalle(page, pedido)
                        pedido['productos'] = productos
                        result['pedidos'].append(pedido)
                        result['stats']['total_productos'] += len(productos)
                    except Exception as e:
                        log(f"⚠ Error en pedido {pedido['numero']}: {e}")
                
                result['success'] = True
                result['stats']['total_pedidos'] = len(result['pedidos'])
                log(f"✅ Extracción completada: {len(result['pedidos'])} pedidos, {result['stats']['total_productos']} productos")
            
            context.close()
            browser.close()
    
    except Exception as e:
        log(f"❌ Error: {e}")
        result['error'] = str(e)
        return 1
    
    # Guardar JSON
    log(f"💾 Guardando resultado en {args.output}...")
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    log("=" * 60)
    log("✅ Proceso completado")
    log("=" * 60)
    
    return 0 if result['success'] else 1

if __name__ == '__main__':
    sys.exit(main())
