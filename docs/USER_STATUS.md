# Estado de la Aplicación — Para Cualquier Persona

**LAFM Crypto Trading Terminal** — Versión 1.0.1  
**Fecha:** 29 de julio de 2026

---

## ¿Qué es esto?

Es un programa de escritorio para Windows que te ayuda a operar con criptomonedas en Binance. Funciona como una estación de trading profesional: muestra gráficos de velas, genera señales de compra/venta, coloca órdenes automáticamente y administra tu riesgo — todo sin depender de servicios en la nube.

**Piáralo como una oficina de trading dentro de tu computadora.**

---

## ¿Qué hace bien?

### ✅ Ya funciona

1. **Instalación real**
   - Tienes un instalador `.exe` listo para distribuir.
   - Se instala como cualquier programa Windows con acceso directo.

2. **Gráficos profesionales**
   - Muestra velas japonesas en tiempo real.
   - Puedes cambiar de timeframe (1m, 5m, 15m, 1h, etc.).
   - Incluye herramientas de dibujo sobre el gráfico.

3. **Trading automático**
   - Modo paper trading con $10,000 de prueba.
   - Órdenes: Market, Limit, Stop-Limit, OCO (TP + SL juntos).
   - Cálculo automático de TP/SL sugeridos según volatilidad (ATR).

4. **Señales inteligentes**
   - Analiza EMA, RSI, MACD, Bollinger Bands.
   - Combina análisis técnico con IA local (ONNX) o modelo heurístico si no hay modelo entrenado.

5. **Gestión de licencias**
   - Cada licencia está atada a la computadora del usuario (HWID).
   - El dueño del sistema puede generar licencias desde su máquina.
   - Panel de administración remoto para emitir, listar y revocar licencias.

6. **Conexión a Binance**
   - Datos de mercado en vivo por WebSocket.
   - Si se corta Internet, sigue funcionando con datos simulados.
   - Las API keys del usuario se guardan encriptadas en su propia PC.

7. **Diseño profesional**
   - Interfaz oscura, animada, con onboarding paso a paso.
   - Notificaciones flotantes para señales y alertas.
   - Responsive y adaptable a diferentes tamaños de pantalla.

---

## ¿Qué hace falta?

### ⚠️ Falta completar

| Feature | Estado actual | ¿Qué falta? |
|---------|---------------|-------------|
| **Modelo IA entrenado** | Usa modelo heurístico | Entrenar el modelo ONNX con datos históricos de Binance |
| **Backtesting integrado** | Router existe pero no montado | Integrar en API principal y conectar con dominio/riesgo |
| **Frontend TypeScript** | React + JSX | Migrar a TypeScript strict y arquitectura por capas |
| **Tests backend >90%** | 16/16 tests básicos | Ampliar cobertura a backtest, IA, repositories, CQRS |
| **Licencia admin segura** | Token hardcodeado en `.env` | Cambiar `ADMIN_API_KEY` antes de distribuir |
| **Actualizaciones automáticas** | Configurado sin release | Publicar releases en GitHub |
| **Certificado Authenticode** | Script listo | Firmar el `.exe` para que Windows no lo marque como "desconocido" |
| **Documentación institucional** | Parcial | Agregar USER_MANUAL, SECURITY_AUDIT, ARCHITECTURE, BACKTEST_MANUAL, MLOPS, DEPLOYMENT_ENTERPRISE |
| **Servidor de licencias central** | No implementado | Implementar `lafm-license-server` con JWT offline 30 días |
| `asar` en electron-builder | Deshabilitado | Habilitar para reducir tamaño |

---

## Flujo de Uso

### Para el Usuario Final

```
1. Instala el programa
   ↓
2. Abre la aplicación
   ↓
3. Ve a http://127.0.0.1:8765/api/health y copia su HWID
   ↓
4. Envía el HWID al dueño de LAFM
   ↓
5. Recibe una clave LIC-... por correo/chat
   ↓
6. Pega la clave en la app → ¡Listo!
```

### Para el Dueño del Sistema (LAFM)

```
1. Recibes el HWID de un cliente
   ↓
2. Abres una terminal en la carpeta scripts/
   ↓
3. Ejecutas:
   python generate_license.py --hwid <HWID_DEL_CLIENTE> 365
   ↓
4. Le envías la clave LIC-... al cliente
   ↓
5. El cliente la activa en su app
```

Si necesitás controlar, revocar o ver todas las licencias:
```powershell
curl -H "X-Admin-Token: <tu_token>" http://127.0.0.1:8765/api/admin/licenses
```

---

## Archivos Importantes

| Archivo | Para qué sirve |
|---------|----------------|
| `backend/dist/trading_app.exe` | El motor backend compilado |
| `dist-electron/*.exe` | Instalador final para usuarios |
| `scripts/generate_license.py` | Generador de licencias |
| `backend/.env` | Configuración (puertos, secretos, CORS) |
| `docs/LICENSE_DISTRIBUTION.md` | Guía de licencias |
| `docs/TECHNICAL_STATUS.md` | Estado técnico completo |

---

## Requisitos del Sistema

- **Windows 10/11** (64-bit)
- **4 GB RAM** mínimo (8 GB recomendado)
- **500 MB** espacio en disco
- **Internet** para datos de mercado de Binance

---

## Seguridad

- Las API keys de Binance se guardan **encriptadas en tu PC**.
- LAFM **nunca** recibe tus credenciales.
- Las licencias están atadas a tu hardware; no se pueden compartir entre máquinas.
- Si perdés tu licencia, contactá a LAFM con tu HWID para una nueva.

---

## Contacto

- **Email:** support@lafm
- **Repo:** https://github.com/Naviplop/cripto-tradin-app

---

## Resumen Ejecutivo

**¿Qué tengo listo para entregar?**
- Un instalador Windows funcional.
- Una app de trading con gráficos, señales, órdenes automáticas y paper trading.
- Sistema de licencias HWID-bound con panel de administración.
- Documentación básica lista.

**¿Qué falta para producción institucional?**
- Entrenar el modelo ONNX real.
- Completar migración Clean Architecture + SQLAlchemy 2.0 + CQRS.
- Integrar backtesting y alcanzar cobertura > 90%.
- Migrar frontend a TypeScript strict.
- Cambiar token admin, firmar `.exe`, publicar releases y completar documentación enterprise.
