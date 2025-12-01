#!/usr/bin/env python3
"""
GardenSeeds Pedidos Extractor
Extrae pedidos usando Playwright y los guarda en JSON para PrestaShop
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

# Configuración
BASE_URL = "https://www.gardenseedstrading.com"
USERNAME = "EUROGROW"
PASSWORD = "Eurogrow1234"

def log(msg):
    """Log con timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

def login(page):
    """Realizar login en GardenSeeds"""
    log("Navegando a home...")
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
    
    log("Buscando botón de login...")
    try:
        # Intentar varias formas de abrir el modal de login
        try:
            page.get_by_text("Iniciar Sesión", exact=False).first.click(timeout=4000)
        except:
            try:
                page.locator("text=Iniciar Sesión").first.click(timeout=3000)
            except:
                # Disparar evento Alpine.js
                page.evaluate("""
                    try {
                        document.dispatchEvent(new CustomEvent('mostrarlogin'));
                        window.dispatchEvent(new CustomEvent('mostrarlogin'));
                    } catch (e) {}
                """)
        
        log("Esperando formulario de login...")
        page.wait_for_selector("#iniciosesion, form#iniciosesion", timeout=15000)
        
        log("Rellenando credenciales...")
        if page.locator("#usuario").count():
            page.fill("#usuario", USERNAME)
        else:
            page.fill("input[name='usuario']", USERNAME)
        
        if page.locator("#password").count():
            page.fill("#password", PASSWORD)
        else:
            page.fill("input[name='password']", PASSWORD)
        
        log("Enviando formulario...")
        # Intentar hacer clic en botón submit
        clicked = False
        for sel in [
            "#iniciosesion button[type='submit']",
            "form#iniciosesion button:has-text('ACCEDER')",
            "text=ACCEDER"
        ]:
            try:
                page.click(sel, timeout=3000)
                clicked = True
                break
            except:
                continue
        
        if not clicked:
            page.evaluate("document.getElementById('iniciosesion').submit()")
        
        log("Esperando confirmación de login...")
        page.wait_for_load_state("networkidle", timeout=20000)
        
        # Verificar que el login fue exitoso
        login_ok = False
        for sel in ["text=Mi cuenta", "text=Salir", "text=Pedidos"]:
            try:
                if page.locator(sel).first.is_visible():
                    login_ok = True
                    break
            except:
                continue
        
        if not login_ok:
            raise Exception("Login falló - no se detectó sesión iniciada")
        
        log("✓ Login exitoso")
        return True
        
    except Exception as e:
        log(f"✗ Error en login: {e}")
        return False

def get_pedidos(page, fecha):
    """Obtener pedidos de una fecha específica"""
    log(f"Navegando a página de pedidos...")
    page.goto(f"{BASE_URL}/micuenta/pedidos", wait_until="domcontentloaded", timeout=45000)
    
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except:
        pass
    
    log("Parseando tabla de pedidos...")
    
    # Esperar a que aparezca la tabla
    try:
        page.wait_for_selector("table.fondoblanco", timeout=10000)
    except:
        log("✗ No se encontró tabla de pedidos")
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
    
    # Convertir fecha de dd/mm/yyyy a yyyy-mm-dd y filtrar
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
    
    log(f"✓ {len(pedidos_filtrados)} pedidos coinciden con fecha {fecha}")
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
    parser = argparse.ArgumentParser(description='Extraer pedidos de GardenSeeds')
    parser.add_argument('--date', type=str, help='Fecha en formato YYYY-MM-DD (default: ayer)')
    parser.add_argument('--output', type=str, default='gardenseeds_pedidos.json', help='Archivo JSON de salida')
    parser.add_argument('--headless', action='store_true', help='(ignorado, siempre headless)')
    args = parser.parse_args()
    
    # Fecha a buscar (por defecto ayer)
    if args.date:
        fecha = args.date
    else:
        fecha = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    log(f"=== GardenSeeds Pedidos Extractor ===")
    log(f"Fecha objetivo: {fecha}")
    log(f"Salida: {args.output}")
    
    result = {
        'success': False,
        'fecha': fecha,
        'timestamp': datetime.now().isoformat(),
        'pedidos': [],
        'error': None
    }
    
    try:
        with sync_playwright() as p:
            log("Iniciando navegador...")
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled"
                ]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1600, "height": 1000}
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
                # Obtener detalle de cada pedido
                for pedido in pedidos:
                    try:
                        productos = get_pedido_detalle(page, pedido)
                        pedido['productos'] = productos
                        result['pedidos'].append(pedido)
                    except Exception as e:
                        log(f"✗ Error obteniendo detalle de {pedido['numero']}: {e}")
                
                result['success'] = True
                log(f"✓ Extracción completada: {len(result['pedidos'])} pedidos")
            
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
