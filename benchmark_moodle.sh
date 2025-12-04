#!/bin/bash
# Script para medir tiempos de creación de imágenes y despliegue de Moodle
# Uso: ./benchmark_moodle.sh

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuración
CONFIG_FILE="tectonic.ini"
LAB_EDITION="examples/moodle_minimal.yml"
LOG_FILE="moodle_benchmark_$(date +%Y%m%d_%H%M%S).log"

# Función para imprimir con timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Función para imprimir sección
section() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    log "=== $1 ==="
}

# Función para medir tiempo de comando
measure_time() {
    local start_time=$(date +%s)
    local description="$1"
    shift
    
    log "Iniciando: $description"
    echo -e "${YELLOW}⏳ Ejecutando: $description${NC}"
    
    if "$@"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        local minutes=$((duration / 60))
        local seconds=$((duration % 60))
        
        log "Completado: $description - Tiempo: ${minutes}m ${seconds}s"
        echo -e "${GREEN}✅ Completado: $description - Tiempo: ${minutes}m ${seconds}s${NC}"
        
        return $duration
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log "ERROR: $description falló después de ${duration}s"
        echo -e "${RED}❌ ERROR: $description falló${NC}"
        return 1
    fi
}

# Banner inicial
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     Benchmark de Despliegue de Moodle en Tectonic         ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

log "Iniciando benchmark de Moodle"
log "Config: $CONFIG_FILE"
log "Lab Edition: $LAB_EDITION"

# Variables para almacenar tiempos
CLEANUP_TIME=0
IMAGE_CREATION_TIME=0
DEPLOY_TIME=0
TOTAL_TIME=0

# 1. Limpieza
section "1. Limpieza de despliegues anteriores"
start_cleanup=$(date +%s)
if poetry run tectonic --config "$CONFIG_FILE" "$LAB_EDITION" destroy \
    --machines \
    --images \
    --moodle \
    --force 2>&1 | tee -a "$LOG_FILE"; then
    end_cleanup=$(date +%s)
    CLEANUP_TIME=$((end_cleanup - start_cleanup))
    log "Limpieza completada en ${CLEANUP_TIME}s"
else
    log "Limpieza falló o no había nada que limpiar"
    CLEANUP_TIME=0
fi

# 2. Creación de imágenes
section "2. Creación de imagen base de Moodle"
start_images=$(date +%s)
if measure_time "Creación de imagen de Moodle" \
    poetry run tectonic --config "$CONFIG_FILE" "$LAB_EDITION" create-images \
    --moodle 2>&1 | tee -a "$LOG_FILE"; then
    end_images=$(date +%s)
    IMAGE_CREATION_TIME=$((end_images - start_images))
else
    echo -e "${RED}❌ Error al crear imágenes${NC}"
    exit 1
fi

# 3. Despliegue
section "3. Despliegue de Moodle"
start_deploy=$(date +%s)
if measure_time "Despliegue de Moodle" \
    poetry run tectonic --config "$CONFIG_FILE" "$LAB_EDITION" deploy \
    --force 2>&1 | tee -a "$LOG_FILE"; then
    end_deploy=$(date +%s)
    DEPLOY_TIME=$((end_deploy - start_deploy))
else
    echo -e "${RED}❌ Error en el despliegue${NC}"
    exit 1
fi

# Calcular tiempo total
TOTAL_TIME=$((CLEANUP_TIME + IMAGE_CREATION_TIME + DEPLOY_TIME))

# 4. Obtener información
section "4. Obteniendo información del despliegue"
poetry run tectonic --config "$CONFIG_FILE" "$LAB_EDITION" info 2>&1 | tee -a "$LOG_FILE"

# 5. Resumen final
section "Resumen de Tiempos"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                    RESULTADOS DEL BENCHMARK                ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Función para formatear tiempo
format_time() {
    local seconds=$1
    local minutes=$((seconds / 60))
    local secs=$((seconds % 60))
    if [ $minutes -gt 0 ]; then
        echo "${minutes}m ${secs}s"
    else
        echo "${secs}s"
    fi
}

echo -e "${CYAN}Limpieza:${NC}           $(format_time $CLEANUP_TIME)"
echo -e "${CYAN}Creación de imágenes:${NC} $(format_time $IMAGE_CREATION_TIME)"
echo -e "${CYAN}Despliegue:${NC}          $(format_time $DEPLOY_TIME)"
echo -e "${CYAN}───────────────────────────────────────────────────────────${NC}"
echo -e "${GREEN}Tiempo total:${NC}       $(format_time $TOTAL_TIME)"
echo ""

# Guardar resumen en log
log "═══════════════════════════════════════════════════════════"
log "RESUMEN DE TIEMPOS:"
log "  Limpieza:           $(format_time $CLEANUP_TIME)"
log "  Creación imágenes: $(format_time $IMAGE_CREATION_TIME)"
log "  Despliegue:         $(format_time $DEPLOY_TIME)"
log "  ───────────────────────────────────────────────────────"
log "  Tiempo total:       $(format_time $TOTAL_TIME)"
log "═══════════════════════════════════════════════════════════"

echo -e "${GREEN}✅ Benchmark completado exitosamente${NC}"
echo -e "${CYAN}📄 Log guardado en: $LOG_FILE${NC}"
echo ""

# Mostrar información de acceso
echo -e "${YELLOW}💡 Para obtener credenciales y URL de acceso:${NC}"
echo "   poetry run tectonic --config $CONFIG_FILE $LAB_EDITION info"
echo ""

