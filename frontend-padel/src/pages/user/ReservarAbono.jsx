// src/pages/user/ReservarAbono.jsx
import React, { useContext, useEffect, useMemo, useState } from "react";
import { AuthContext } from "../../auth/AuthContext";
import { axiosAuth } from "../../utils/axiosAuth";
import {
  Box, Text, HStack, VStack, Select, useToast, Badge, Divider, useDisclosure,
  FormControl, FormLabel, Stack, Skeleton, Alert, AlertIcon, Input as ChakraInput,
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalCloseButton, ModalBody, ModalFooter
} from "@chakra-ui/react";

import Button from "../../components/ui/Button";
import { useCardColors, useInputColors, useMutedText } from "../../components/theme/tokens";
import ReservaPagoModalAbono from "../../components/modals/ReservaPagoModalAbono.jsx";

const DIAS = [
  { value: 0, label: "Lunes" },
  { value: 1, label: "Martes" },
  { value: 2, label: "Miércoles" },
  { value: 3, label: "Jueves" },
  { value: 4, label: "Viernes" },
  { value: 5, label: "Sábado" },
  { value: 6, label: "Domingo" },
];
const LABELS = { x1: "Individual", x2: "2 Personas", x3: "3 Personas", x4: "4 Personas" };

// Función para mostrar configuración personalizada de manera legible
const mostrarConfiguracionPersonalizada = (configuracion, tiposClase) => {
  if (!configuracion || !Array.isArray(configuracion)) return "Personalizado";
  
  const configs = configuracion
    .filter(config => config.tipo_clase_id)
    .map(config => {
      const tipoClase = tiposClase.find(tc => tc.id === config.tipo_clase_id);
      const nombre = tipoClase?.nombre || LABELS[tipoClase?.codigo] || "Tipo";
      return `${config.cantidad}x ${nombre}`;
    });
  
  return configs.length > 0 ? configs.join(", ") : "Personalizado";
};

const ABONO_OPCIONES = [
  { codigo: "x1", nombre: "Individual" },
  { codigo: "x2", nombre: "2 Personas" },
  { codigo: "x3", nombre: "3 Personas" },
  { codigo: "x4", nombre: "4 Personas" },
  { codigo: "personalizado", nombre: "Personalizado" },
];

const ReservarAbono = ({ onClose }) => {
  const { accessToken } = useContext(AuthContext);
  const api = useMemo(() => (accessToken ? axiosAuth(accessToken) : null), [accessToken]);

  const toast = useToast();
  const card = useCardColors();
  const input = useInputColors();
  const muted = useMutedText();

  const pagoDisc = useDisclosure();
  const configDisc = useDisclosure();
  const [abonoParaConfigurar, setAbonoParaConfigurar] = useState(null);

  // ===== ESTADOS DEL COMPONENTE =====
  // Estados para "Mis abonos" (abonos del usuario actual)
  const [loadingAbonos, setLoadingAbonos] = useState(true);
  const [misAbonos, setMisAbonos] = useState([]);
  const [abonosPorVencer, setAbonosPorVencer] = useState([]);
  const [showRenewBanner, setShowRenewBanner] = useState(false);
  const [renovandoAbonoId, setRenovandoAbonoId] = useState(null);

  // Estados para filtros de nueva reserva (sede, profesor, día, tipo)
  const [sedes, setSedes] = useState([]);
  const [profesores, setProfesores] = useState([]);
  const [diasDisponibles, setDiasDisponibles] = useState([]);
  const [sedeId, setSedeId] = useState("");
  const [profesorId, setProfesorId] = useState("");
  const [diaSemana, setDiaSemana] = useState("");
  const [horaFiltro, setHoraFiltro] = useState("");
  const [tiposAbono, setTiposAbono] = useState([]);
  const [tiposClase, setTiposClase] = useState([]);
  const [tipoAbono, setTipoAbono] = useState("");
  const [abonosLibres, setAbonosLibres] = useState([]);
  const [loadingDisponibles, setLoadingDisponibles] = useState(false);
  const [selectedBonos, setSelectedBonos] = useState([]);

  // Estados para configuración de abonos personalizados
  const [configuracionPersonalizada, setConfiguracionPersonalizada] = useState([]);

  // Estados para selección y pago (diferente al admin, aquí SÍ hay pago)
  const [seleccion, setSeleccion] = useState(null);
  const [archivo, setArchivo] = useState(null);
  const [bonificaciones, setBonificaciones] = useState([]);
  const [usarBonificado, setUsarBonificado] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [modoRenovacion, setModoRenovacion] = useState(false);

  // Estados para información de pago
  const configPago = { tiempo_maximo_minutos: 15 };

  const now = new Date();
  const anioActual = now.getFullYear();
  const mesActual = now.getMonth() + 1;

  // ===== USEMEMO Y HELPERS =====
  // useMemo: Evita recálculos cuando sedes/profesores no cambian
  const sedeSel = useMemo(
  () => sedes.find(s => String(s.id) === String(sedeId)) || null,
  [sedes, sedeId]
  );
  const profSel = useMemo(
    () => profesores.find(p => String(p.id) === String(profesorId)) || null,
    [profesores, profesorId]
  );

  // Helpers: Funciones utilitarias
  const fmtHora = (h) => (h || "").slice(0, 5);
  const proximoMes = (anio, mes) => (mes === 12 ? { anio: anio + 1, mes: 1 } : { anio, mes: mes + 1 });

  // ===== USEEFFECT - LLAMADAS AL BACKEND =====
  // 1) Cargar "Mis abonos" del usuario
  // GET /api/padel/abonos/mios/ → Filtra abonos por vencer para banner
  useEffect(() => {
    if (!api) return;
    setLoadingAbonos(true);
    api.get("padel/abonos/mios/")
      .then((res) => {
        const data = res?.data?.results ?? res?.data ?? [];
        const arr = Array.isArray(data) ? data : [];
        setMisAbonos(arr);
        const porVencer = arr.filter(
          (a) => a?.ventana_renovacion === true && !a?.renovado && a?.estado_vigencia === "activo"
        );
        setAbonosPorVencer(porVencer);
        setShowRenewBanner(porVencer.length > 0);
      })
      .catch(() => {
        setMisAbonos([]);
        setAbonosPorVencer([]);
        setShowRenewBanner(false);
      })
      .finally(() => setLoadingAbonos(false));
  }, [api]);

  // 2) Cargar sedes disponibles
  // GET /api/turnos/sedes/ → Sedes con alias y CBU para pagos
  useEffect(() => {
    if (!api) return;
    api.get("turnos/sedes/")
      .then(res => {
        const data = res?.data?.results ?? res?.data ?? [];
        setSedes(Array.isArray(data) ? data : []);
      })
      .catch(() => setSedes([]));
  }, [api]);

  // 3) profesores - cargar todos los profesores de la sede
  useEffect(() => {
    if (!api || !sedeId) { 
      setProfesores([]); 
      setProfesorId(""); // Limpiar selección de profesor
      return; 
    }
    
    api.get(`turnos/prestadores/?lugar_id=${sedeId}`)
      .then(res => {
        const data = res?.data?.results ?? res?.data ?? [];
        setProfesores(Array.isArray(data) ? data : []);
      })
      .catch(e => { 
        console.error("[AbonoUser] profesores error:", e); 
        setProfesores([]); 
      });
  }, [api, sedeId]);

  // 3.1) Filtrar días disponibles del profesor seleccionado
  // - Extrae días de la semana de las disponibilidades del profesor
  // - Solo muestra días donde el profesor tiene disponibilidad activa
  useEffect(() => {
    if (!profesorId || !profesores.length) {
      setDiasDisponibles([]);
      return;
    }
    
    const profesor = profesores.find(p => String(p.id) === String(profesorId));
    if (profesor?.disponibilidades) {
      const diasDisponibles = profesor.disponibilidades
        .filter(d => d.activo && d.lugar === Number(sedeId)) // Solo de la sede actual
        .map(d => d.dia_semana);
      
      setDiasDisponibles(diasDisponibles);
    } else {
      setDiasDisponibles([]);
    }
  }, [profesorId, profesores, sedeId]);

  // 4) Cargar abonos disponibles
  // GET /api/padel/abonos/disponibles/ → Abonos libres para reservar
  // - Ya no usa tipo_codigo: el backend calculará precios dinámicamente
  // - Para personalizados: procesa datos para mostrar solo horas disponibles
  // - Para normales: usa los datos tal como vienen del backend
  useEffect(() => {
    const ready = api && sedeId && profesorId && (diaSemana !== "") && tipoAbono;
    if (!ready) { setAbonosLibres([]); return; }
    const params = new URLSearchParams({
      sede_id: String(sedeId),
      prestador_id: String(profesorId),
      dia_semana: String(diaSemana),
      anio: String(anioActual),
      mes: String(mesActual),
    });
    
    // Ya no necesitamos tipo_codigo para obtener disponibilidad
    // El backend calculará precios dinámicamente
    
    if (horaFiltro) params.append("hora", horaFiltro);

    setLoadingDisponibles(true);
    api.get(`padel/abonos/disponibles/?${params.toString()}`)
      .then(res => {
        let data = res?.data?.results ?? res?.data ?? [];
        
        if (tipoAbono === "personalizado") {
          // Para abonos personalizados, mostrar todas las horas disponibles
          // pero marcar cada una como "Personalizado" sin tipo_clase específico
          data = data.map(item => ({
            hora: item.hora,
            tipo_clase: null // No hay tipo específico, se configurará en el modal
          }));
        } else {
          // Para abonos normales, usar los datos tal como vienen del backend
          data = Array.isArray(data) ? data : [];
        }
        
        setAbonosLibres(data);
      })
      .catch(() => {
        setAbonosLibres([]);
        toast({ title: "No se pudieron cargar abonos libres", status: "error", duration: 4000 });
      })
      .finally(() => setLoadingDisponibles(false));
  }, [api, sedeId, profesorId, diaSemana, horaFiltro, tipoAbono, anioActual, mesActual, toast]);

  // Tipos de abono con precio
  useEffect(() => {
    if (!api || !sedeId) { setTiposAbono([]); return; }
    api.get(`padel/tipos-abono/?sede_id=${sedeId}`)
      .then(res => {
        const data = res?.data?.results ?? res?.data ?? [];
        setTiposAbono(Array.isArray(data) ? data : []);
      })
      .catch(() => setTiposAbono([]));
  }, [api, sedeId]);

  // Tipos de clase para configuración personalizada
  useEffect(() => {
    if (!api || !sedeId) { setTiposClase([]); return; }
    api.get(`padel/tipos-clase/?sede_id=${sedeId}`)
      .then(res => {
        const data = res?.data?.results ?? res?.data ?? [];
        setTiposClase(Array.isArray(data) ? data : []);
      })
      .catch(() => setTiposClase([]));
  }, [api, sedeId]);

  const precioAbonoPorCodigo = useMemo(() => {
    const map = {};
    (tiposAbono || []).forEach(a => { map[a.codigo] = Number(a.precio); });
    return map;
  }, [tiposAbono]);

  const precioAbonoActual = (tipoCodigo, tipoObj) => {
    if (tipoCodigo && precioAbonoPorCodigo[tipoCodigo] != null) return Number(precioAbonoPorCodigo[tipoCodigo]);
    if (tipoObj && tipoObj.precio != null) return Number(tipoObj.precio);
    return 0;
  };

  // Función para calcular turnos del mes para un día de la semana específico
  const calcularTurnosDelMes = (anio, mes, diaSemana, soloFuturos = true) => {
    // Configuración de anticipación mínima (en horas)
    const HORAS_ANTICIPACION_MINIMA = 1;
    
    const hoy = new Date();
    
    console.log('🔍 DEBUG calcularTurnosDelMes - INICIO:', {
      anio,
      mes,
      diaSemana,
      soloFuturos,
      hoy: hoy.toISOString()
    });
    
    // Contar días del mes que caen en el día de la semana
    const diasEnMes = new Date(anio, mes, 0).getDate(); // Último día del mes (corregido)
    let diasContados = 0;
    
    // Para comparaciones de fecha, usar solo la fecha sin hora
    const hoySinHora = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());
    
    console.log('🔍 DEBUG calcularTurnosDelMes - CONFIG:', {
      diasEnMes,
      hoySinHora: hoySinHora.toISOString(),
      HORAS_ANTICIPACION_MINIMA
    });
    
    for (let dia = 1; dia <= diasEnMes; dia++) {
      const fecha = new Date(anio, mes - 1, dia);
      
      if (fecha.getDay() === diaSemana) {
        console.log(`🔍 DEBUG calcularTurnosDelMes - DÍA ${dia}:`, {
          fecha: fecha.toDateString(),
          diaSemana: fecha.getDay(),
          targetDiaSemana: diaSemana,
          esDiaCorrecto: fecha.getDay() === diaSemana
        });
        
        if (soloFuturos) {
          // Para el mes actual: solo contar fechas futuras con anticipación
          const fechaSinHora = new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate());
          
          console.log(`🔍 DEBUG calcularTurnosDelMes - COMPARACIÓN:`, {
            fechaSinHora: fechaSinHora.toISOString(),
            hoySinHora: hoySinHora.toISOString(),
            esFuturo: fechaSinHora > hoySinHora,
            esHoy: fechaSinHora.getTime() === hoySinHora.getTime()
          });
          
          if (fechaSinHora >= hoySinHora) {
            // Fechas futuras O HOY: incluir todas
            if (fechaSinHora.getTime() === hoySinHora.getTime()) {
              // Es hoy: verificar anticipación mínima
              const horaActual = hoy.getHours();
              const horaMaxima = 24 - HORAS_ANTICIPACION_MINIMA;
              const incluirHoy = horaActual < horaMaxima;
              
              console.log(`🔍 DEBUG calcularTurnosDelMes - DÍA ACTUAL:`, {
                horaActual,
                horaMaxima,
                incluirHoy,
                HORAS_ANTICIPACION_MINIMA
              });
              
              if (incluirHoy) {
                diasContados++;
                console.log(`✅ DEBUG: Incluyendo día actual ${fecha.toDateString()} (hora actual: ${horaActual})`);
              } else {
                console.log(`❌ DEBUG: Excluyendo día actual ${fecha.toDateString()} (hora actual: ${horaActual} >= ${horaMaxima})`);
              }
            } else {
              // Es futuro: incluir siempre
              diasContados++;
              console.log(`✅ DEBUG: Incluyendo día futuro ${fecha.toDateString()}`);
            }
          } else {
            console.log(`❌ DEBUG: Excluyendo día pasado ${fecha.toDateString()}`);
          }
        } else {
          // Para el mes siguiente: contar todos los días
          diasContados++;
          console.log(`✅ DEBUG: Incluyendo día del mes siguiente ${fecha.toDateString()}`);
        }
      }
    }
    
    console.log(`🔍 DEBUG calcularTurnosDelMes - RESULTADO:`, {
      anio,
      mes,
      diaSemana,
      soloFuturos,
      diasContados,
      diasEnMes
    });
    
    return diasContados;
  };

  // ======= CONFIGURACIÓN PERSONALIZADA =======
  // 10) Gestión de configuración personalizada
  // Funciones para agregar, remover y actualizar tipos de clase en abonos personalizados
  const agregarTipoClase = () => {
    if (tiposClase.length === 0) return;
    const nuevoTipo = {
      tipo_clase_id: tiposClase[0].id,
      cantidad: 1,
      codigo: tiposClase[0].codigo
    };
    setConfiguracionPersonalizada([...configuracionPersonalizada, nuevoTipo]);
  };

  const removerTipoClase = (index) => {
    const nuevaConfig = configuracionPersonalizada.filter((_, i) => i !== index);
    setConfiguracionPersonalizada(nuevaConfig);
  };

  const actualizarTipoClase = (index, campo, valor) => {
    const nuevaConfig = [...configuracionPersonalizada];
    nuevaConfig[index] = { ...nuevaConfig[index], [campo]: valor };
    
    // Si se cambia el tipo_clase_id, actualizar también el codigo
    if (campo === 'tipo_clase_id') {
      const tipoClase = tiposClase.find(tc => tc.id === valor);
      if (tipoClase) {
        nuevaConfig[index].codigo = tipoClase.codigo;
      }
    }
    
    setConfiguracionPersonalizada(nuevaConfig);
  };

  // 11) Cálculo de monto personalizado
  // Suma (cantidad × precio) para cada tipo de clase configurado
  const calcularMontoPersonalizado = () => {
    return configuracionPersonalizada.reduce((total, config) => {
      const tipoClase = tiposClase.find(tc => tc.id === config.tipo_clase_id);
      if (tipoClase) {
        return total + (Number(tipoClase.precio) * config.cantidad);
      }
      return total;
    }, 0);
  };

  // 12) Cálculo de turnos disponibles
  // Cuenta turnos reales disponibles para el día y hora específicos del mes
  const calcularMaximoTurnos = () => {
    // Calcular turnos del mes independientemente de abonosLibres
    const hoy = new Date();
    const anio = hoy.getFullYear();
    const mes = hoy.getMonth() + 1;
    const diaSemanaSeleccionado = Number(diaSemana) || 0; // 0 = lunes
    
    // Usar la función centralizada con soloFuturos = true para el mes actual
    const turnos = calcularTurnosDelMes(anio, mes, diaSemanaSeleccionado, true);
    
    console.log('🔍 DEBUG calcularMaximoTurnos:', {
      hoy: hoy.toISOString(),
      anio,
      mes,
      diaSemanaSeleccionado,
      turnos,
      tipoAbono,
      sedeId,
      profesorId
    });
    
    // 🚨 TEMPORAL: Si devuelve 0, forzar 1 para debug
    if (turnos === 0) {
      console.log('🚨 DEBUG: calcularMaximoTurnos devolvió 0, forzando 1 para debug');
      return 1;
    }
    
    return turnos;
  };

  // 13) Validación de turnos
  // Funciones para verificar que no se exceda el límite de turnos disponibles
  const calcularTurnosAsignados = () => {
    return configuracionPersonalizada.reduce((total, config) => total + config.cantidad, 0);
  };

  const calcularTurnosRestantes = () => {
    return calcularMaximoTurnos() - calcularTurnosAsignados();
  };

  // 14) Abrir modal de pago (nueva reserva)
  // Para abonos normales va directo al pago, para personalizados abre configuración
  const abrirPagoReservaNueva = async (item) => {
    if (tipoAbono === "personalizado") {
      // Para abonos personalizados, abrir modal de configuración
      setAbonoParaConfigurar(item);
      
      // Asegurar que los tipos de clase estén cargados ANTES de inicializar
      if (tiposClase.length === 0 && api && sedeId) {
        api.get(`padel/tipos-clase/?sede_id=${sedeId}`)
          .then(res => {
            const data = res?.data?.results ?? res?.data ?? [];
            const tiposCargados = Array.isArray(data) ? data : [];
            setTiposClase(tiposCargados);
            
            // Inicializar configuración personalizada con TODOS los turnos del mes (obligatorio configurar cada uno)
            const turnosDelMes = calcularMaximoTurnos();
            const configuracionInicial = Array.from({ length: turnosDelMes }, (_, index) => ({
              tipo_clase_id: tiposCargados.length > 0 ? tiposCargados[0].id : null,
              cantidad: 1,
              codigo: tiposCargados.length > 0 ? tiposCargados[0].codigo : null
            }));
            setConfiguracionPersonalizada(configuracionInicial);
          })
          .catch(() => {
            setTiposClase([]);
            // Inicializar con array vacío si no se pueden cargar los tipos
            const turnosDelMes = calcularMaximoTurnos();
            const configuracionInicial = Array.from({ length: turnosDelMes }, (_, index) => ({
              tipo_clase_id: null,
              cantidad: 1,
              codigo: null
            }));
            setConfiguracionPersonalizada(configuracionInicial);
          });
      } else {
        // Si ya están cargados, inicializar directamente
        const turnosDelMes = calcularMaximoTurnos();
        const configuracionInicial = Array.from({ length: turnosDelMes }, (_, index) => ({
          tipo_clase_id: tiposClase.length > 0 ? tiposClase[0].id : null,
          cantidad: 1,
          codigo: tiposClase.length > 0 ? tiposClase[0].codigo : null
        }));
        setConfiguracionPersonalizada(configuracionInicial);
      }
      
      configDisc.onOpen();
      return;
    }

    // Para abonos normales, ir directo al modal de pago
    let precioAbono, precioUnit, tipoClase;

    // Calcular precio dinámico basado en turnos del mes
    const tipoClaseSeleccionada = tiposClase.find(tc => tc.codigo === tipoAbono);
    if (tipoClaseSeleccionada) {
      const turnosDelMes = calcularMaximoTurnos();
      precioAbono = Number(tipoClaseSeleccionada.precio) * turnosDelMes;
      precioUnit = Number(tipoClaseSeleccionada.precio);
      tipoClase = tipoClaseSeleccionada;
    } else {
      precioAbono = 0;
      precioUnit = 0;
      tipoClase = null;
    }

    setSeleccion({
      sede: Number(sedeId),
      prestador: Number(profesorId),
      dia_semana: Number(diaSemana),
      hora: item?.hora,
      tipo_clase: tipoClase,
      precio_abono: precioAbono,
      precio_unitario: precioUnit,
      anio: anioActual,
      mes: mesActual,
      alias: sedeSel?.alias || "",
      cbu_cvu: sedeSel?.cbu_cvu || "",
      configuracion_personalizada: null,
    });
    setModoRenovacion(false);
    setArchivo(null);
    setUsarBonificado(false);

    try {
      if (api) {
        const res = await api.get(`turnos/bonificados/mios/`);
        const bonos = res?.data?.results ?? res?.data ?? [];
        setBonificaciones(Array.isArray(bonos) ? bonos : []);
      } else {
        setBonificaciones([]);
      }
    } catch {
      setBonificaciones([]);
    }
    pagoDisc.onOpen();
  };

  // 15) Proceder al pago desde configuración
  // Transición del modal de configuración al modal de pago para abonos personalizados
  const procederAlPago = async () => {
    if (modoRenovacion) {
      // Para renovaciones: actualizar el precio en la selección existente
      const nuevoPrecioAbono = configuracionPersonalizada.reduce((total, config) => {
        const tipoClase = tiposClase.find(tc => tc.id === config.tipo_clase_id);
        return total + (Number(tipoClase?.precio || 0) * config.cantidad);
      }, 0);
      
      console.log('DEBUG procederAlPago renovación:', {
        configuracionPersonalizada,
        nuevoPrecioAbono,
        tiposClase: tiposClase.length
      });
      
      // Actualizar la selección con el nuevo precio
      setSeleccion(prev => ({
        ...prev,
        precio_abono: nuevoPrecioAbono,
        configuracion_personalizada: configuracionPersonalizada,
      }));
      
      configDisc.onClose();
      pagoDisc.onOpen();
    } else {
      // Para abonos nuevos: lógica original
      if (!abonoParaConfigurar) return;

      let precioAbono = calcularMontoPersonalizado();
      let precioUnit = 0;
      let tipoClase = null;

      setSeleccion({
        sede: Number(sedeId),
        prestador: Number(profesorId),
        dia_semana: Number(diaSemana),
        hora: abonoParaConfigurar?.hora,
        tipo_clase: tipoClase,
        precio_abono: precioAbono,
        precio_unitario: precioUnit,
        anio: anioActual,
        mes: mesActual,
        alias: sedeSel?.alias || "",
        cbu_cvu: sedeSel?.cbu_cvu || "",
        configuracion_personalizada: configuracionPersonalizada,
      });
      setModoRenovacion(false);
      setArchivo(null);
      setUsarBonificado(false);
      // Cargar bonificaciones por monto (no por tipo de clase)
      try {
        if (api) {
          const res = await api.get(`turnos/bonificados/mios/`);
          const bonos = res?.data?.results ?? res?.data ?? [];
          setBonificaciones(Array.isArray(bonos) ? bonos : []);
        } else {
          setBonificaciones([]);
        }
      } catch {
        setBonificaciones([]);
      }
      configDisc.onClose();
      pagoDisc.onOpen();
    }
  };

  // 16) Abrir modal de renovación
  // Carga datos del abono existente y calcula precios para el próximo mes
  const abrirRenovarAbono = async (abono) => {
    setRenovandoAbonoId(abono.id);

    const { anio, mes } = proximoMes(Number(abono.anio), Number(abono.mes));

    // Calcular precio dinámico para el mes siguiente
    let precioAbono = 0;
    let precioUnit = 0;
    let tipoClase = null;
    let configuracionPersonalizada = null;

    try {
      const tiposCl = await api.get(`padel/tipos-clase/?sede_id=${abono.sede_id}`);
      const tiposClase = tiposCl?.data?.results ?? tiposCl?.data ?? [];

      console.log('DEBUG abono completo:', { 
        abono, 
        tiene_configuracion_personalizada: !!abono.configuracion_personalizada,
        tiene_tipo_clase_codigo: !!abono.tipo_clase_codigo
      });

      // CASO ESPECIAL: Abono asignado por admin sin tipo_clase ni configuracion_personalizada
      if (!abono.configuracion_personalizada && !abono.tipo_clase_codigo) {
        console.log('DEBUG ABONO LEGACY: Sin tipo_clase ni configuracion_personalizada, usando fallback');
        
        if (tiposClase.length > 0) {
          const tipoClaseDefault = tiposClase[0]; // Usar el primer tipo como fallback
          console.log('DEBUG LEGACY FALLBACK: Usando tipo por defecto:', tipoClaseDefault);
          
          tipoClase = { 
            id: tipoClaseDefault.id, 
            codigo: tipoClaseDefault.codigo, 
            precio: Number(tipoClaseDefault.precio) 
          };
          
          // Calcular turnos del mes siguiente para el día de la semana
          const turnosDelMesSiguiente = calcularTurnosDelMes(anio, mes, abono.dia_semana, false);
          console.log('DEBUG LEGACY renovación:', { anio, mes, diaSemana: abono.dia_semana, turnosDelMesSiguiente, precioUnit: Number(tipoClaseDefault.precio) });
          precioUnit = Number(tipoClaseDefault.precio);
          precioAbono = precioUnit * turnosDelMesSiguiente;
        } else {
          console.log('DEBUG ERROR CRÍTICO: No hay tipos de clase disponibles para abono legacy');
        }
      } else if (abono.configuracion_personalizada) {
        // Abono personalizado: calcular precio basado en configuración
        configuracionPersonalizada = abono.configuracion_personalizada;
        
        // Calcular turnos del mes siguiente para el día de la semana
        const turnosDelMesSiguiente = calcularTurnosDelMes(anio, mes, abono.dia_semana, false);
        console.log('DEBUG renovación personalizada:', { anio, mes, diaSemana: abono.dia_semana, turnosDelMesSiguiente });
        
        // Calcular precio total basado en configuración
        precioAbono = 0;
        for (const config of configuracionPersonalizada) {
          const tipoClaseConfig = tiposClase.find(tc => tc.id === config.tipo_clase_id);
          if (tipoClaseConfig) {
            // Para personalizados, usar la cantidad máxima de turnos del mes
            const cantidadMaxima = Math.min(config.cantidad, turnosDelMesSiguiente);
            precioAbono += Number(tipoClaseConfig.precio) * cantidadMaxima;
            console.log('DEBUG config item:', { config, tipoClaseConfig, cantidadMaxima, precio: Number(tipoClaseConfig.precio) });
          }
        }
        precioUnit = 0; // Para personalizados no hay precio unitario
      } else {
        // Abono normal: calcular precio dinámico
        console.log('DEBUG abono normal:', { 
          abono_tipo_clase_codigo: abono.tipo_clase_codigo, 
          tiposClase_disponibles: tiposClase.map(tc => ({ codigo: tc.codigo, id: tc.id, precio: tc.precio }))
        });
        
        const tipoClaseSeleccionada = tiposClase.find(tc => tc.codigo === abono.tipo_clase_codigo);
        console.log('DEBUG tipoClaseSeleccionada:', tipoClaseSeleccionada);
        
        if (tipoClaseSeleccionada) {
          tipoClase = { 
            id: tipoClaseSeleccionada.id, 
            codigo: tipoClaseSeleccionada.codigo, 
            precio: Number(tipoClaseSeleccionada.precio) 
          };
          
          // Calcular turnos del mes siguiente para el día de la semana
          const turnosDelMesSiguiente = calcularTurnosDelMes(anio, mes, abono.dia_semana, false);
          console.log('DEBUG renovación normal:', { anio, mes, diaSemana: abono.dia_semana, turnosDelMesSiguiente, precioUnit: Number(tipoClaseSeleccionada.precio) });
          precioUnit = Number(tipoClaseSeleccionada.precio);
          precioAbono = precioUnit * turnosDelMesSiguiente;
        } else {
          console.log('DEBUG ERROR: No se encontró tipoClaseSeleccionada para código:', abono.tipo_clase_codigo);
          
          // FALLBACK: Si no hay tipo_clase_codigo, usar el primer tipo disponible como default
          if (tiposClase.length > 0) {
            const tipoClaseDefault = tiposClase[0]; // Usar el primer tipo como fallback
            console.log('DEBUG FALLBACK: Usando tipo por defecto:', tipoClaseDefault);
            
            tipoClase = { 
              id: tipoClaseDefault.id, 
              codigo: tipoClaseDefault.codigo, 
              precio: Number(tipoClaseDefault.precio) 
            };
            
            // Calcular turnos del mes siguiente para el día de la semana
            const turnosDelMesSiguiente = calcularTurnosDelMes(anio, mes, abono.dia_semana, false);
            console.log('DEBUG FALLBACK renovación:', { anio, mes, diaSemana: abono.dia_semana, turnosDelMesSiguiente, precioUnit: Number(tipoClaseDefault.precio) });
            precioUnit = Number(tipoClaseDefault.precio);
            precioAbono = precioUnit * turnosDelMesSiguiente;
          } else {
            console.log('DEBUG ERROR CRÍTICO: No hay tipos de clase disponibles');
          }
        }
      }
      
      console.log('DEBUG precio final:', { precioAbono, precioUnit, tipoClase, configuracionPersonalizada });
    } catch (error) {
      console.error('ERROR en abrirRenovarAbono:', error);
      precioAbono = 0; 
      precioUnit = 0;
    }

    const sedeAbono = sedes.find(s => String(s.id) === String(abono.sede_id));

    setSeleccion({
      sede: abono.sede_id,
      prestador: abono.prestador_id,
      dia_semana: abono.dia_semana,
      hora: abono.hora,
      tipo_clase: tipoClase,
      precio_abono: precioAbono,
      precio_unitario: precioUnit,
      anio, mes,
      alias: sedeAbono?.alias || "",
      cbu_cvu: sedeAbono?.cbu_cvu || "",
      abono_id: abono.id, // 👈 clave para renovación
      configuracion_personalizada: configuracionPersonalizada, // 👈 para abonos personalizados
    });
    setModoRenovacion(true);
    setArchivo(null);
    setUsarBonificado(false);

    try {
      if (api) {
        const res = await api.get(`turnos/bonificados/mios/`);
        const bonos = res?.data?.results ?? res?.data ?? [];
        setBonificaciones(Array.isArray(bonos) ? bonos : []);
      } else {
        setBonificaciones([]);
      }
    } catch {
      setBonificaciones([]);
    }
    pagoDisc.onOpen();
  };

  // 19) Confirmación de pago
  // Procesa reserva o renovación con validación de comprobante y aplicación de bonificaciones
  const onConfirmarPago = async (bonosIds = []) => {
    if (!seleccion) return;

    // Usar la misma lógica que el modal para calcular totalEstimado
    const abonoPrice = Number(seleccion?.precio_abono ?? 0);
    const totalDescuento = (bonosIds || []).reduce((sum, id) => {
      const bono = bonificaciones?.find(b => b.id === id);
      return sum + (Number(bono?.valor) || 0);
    }, 0);
    const totalEstimado = Math.max(0, abonoPrice - totalDescuento);


    if (!archivo && totalEstimado > 0) {
      toast({
        title: "Falta comprobante",
        description: "Subí el comprobante o seleccioná bonificaciones suficientes para cubrir el abono.",
        status: "warning",
        duration: 5000,
      });
      return;
    }

    setEnviando(true);
    try {
      const fd = new FormData();
      fd.append("sede", seleccion.sede);
      fd.append("prestador", seleccion.prestador);
      fd.append("dia_semana", seleccion.dia_semana);
      fd.append("hora", seleccion.hora);
      fd.append("anio", seleccion.anio);
      fd.append("mes", seleccion.mes);
      fd.append("precio_abono", abonoPrice);
      fd.append("precio_unitario", seleccion.precio_unitario || 0);
      fd.append("forzar_admin", false);
      fd.append("usar_bonificado", (bonosIds || []).length > 0);
      // Enviar bonificaciones_ids como múltiples campos individuales
      if (bonosIds && bonosIds.length > 0) {
        bonosIds.forEach(id => fd.append("bonificaciones_ids", id));
      }
      fd.append("restante", totalEstimado);
      
      if (seleccion?.configuracion_personalizada) {
        // Para abonos personalizados
        fd.append("configuracion_personalizada", JSON.stringify(seleccion.configuracion_personalizada));
        fd.append("tipo_clase", ""); // Vacío para personalizados
      } else {
        // Para abonos normales
        fd.append("tipo_clase", seleccion.tipo_clase?.id || "");
        fd.append("configuracion_personalizada", "[]"); // Vacío para normales
      }
      
      if (seleccion?.abono_id) {
        fd.append("abono_id", seleccion.abono_id); // 👈 indica RENOVACIÓN al backend
      }
      if (archivo) fd.append("archivo", archivo);

      console.log('🔍 DEBUG onConfirmarPago - DATOS ENVIADOS:', {
        sede_id: seleccion.sede,
        prestador_id: seleccion.prestador,
        dia_semana: seleccion.dia_semana,
        hora: seleccion.hora,
        anio: seleccion.anio,
        mes: seleccion.mes,
        precio_abono: abonoPrice,
        precio_unitario: seleccion.precio_unitario,
        forzar_admin: false,
        usar_bonificado: (bonosIds || []).length > 0,
        bonificaciones_ids: bonosIds,
        restante: totalEstimado,
        configuracion_personalizada: seleccion.configuracion_personalizada,
        tipo_clase: seleccion.tipo_clase?.id,
        abono_id: seleccion.abono_id,
        tiene_archivo: !!archivo
      });

      await api.post("padel/abonos/reservar/", fd, { headers: { "Content-Type": "multipart/form-data" } });

      toast({
        title: modoRenovacion ? "Abono renovado" : "Abono reservado",
        description: modoRenovacion ? "Se aplicará al próximo mes." : "Pago registrado.",
        status: "success",
        duration: 4500,
      });

      pagoDisc.onClose();
      setArchivo(null);
      setUsarBonificado(false);
      setSeleccion(null);
      setConfiguracionPersonalizada([]); // Limpiar configuración personalizada

      if (modoRenovacion) {
        setMisAbonos(prev =>
          prev.map(a =>
            a.id === renovandoAbonoId ? { ...a, renovado: true, ventana_renovacion: false } : a
          )
        );
        // actualizar banner localmente para que deje de avisar
        setAbonosPorVencer(prev => prev.filter(a => a.id !== renovandoAbonoId));
        setShowRenewBanner(prev => {
          const quedan = abonosPorVencer.filter(a => a.id !== renovandoAbonoId);
          return quedan.length > 0;
        });
        setRenovandoAbonoId(null);
      } else {
        onClose?.();
      }
    } catch (e) {
      // Manejo específico de errores de comprobante
      let msg = "No se pudo completar la operación";
      let title = "Error";
      
      if (e?.response?.data?.comprobante) {
        // Error específico de comprobante - mensaje genérico para el usuario
        title = "Comprobante inválido";
        msg = "El comprobante no es válido. Verificá que sea un comprobante de pago real y que corresponda a la sede seleccionada.";
      } else if (e?.response?.data?.error) {
        msg = e.response.data.error;
      } else if (e?.response?.data?.detail) {
        msg = e.response.data.detail;
      } else if (e?.message) {
        msg = e.message;
      }
      
      toast({ title, description: msg, status: "error", duration: 5000 });
    } finally {
      setEnviando(false);
    }
  };

  const modalIsRenderable = typeof ReservaPagoModalAbono === "function";

  // === UI ===
  return (
    <Box w="100%" maxW="1000px" mx="auto" mt={8} p={6} bg={card.bg} color={card.color} rounded="xl" boxShadow="2xl">
      
      {showRenewBanner && (
        <Alert status="warning" mb={4} rounded="md">
          <AlertIcon />
          <Box>
            <Text fontWeight="semibold" mb={1}>
              Tenés abonos por vencer en menos de 7 días:
            </Text>
            <VStack align="stretch" spacing={1}>
              {abonosPorVencer.map((a) => (
                <HStack key={a.id} justify="space-between">
                  <Text fontSize="sm">
                    {a.dia_semana_label} · {fmtHora(a.hora)} hs — vence {a.vence_el || "—"} ({String(a.mes).padStart(2,"0")}/{a.anio})
                  </Text>
                </HStack>
              ))}
            </VStack>
          </Box>
        </Alert>
      )}

      {/* === Mis abonos (arriba) === */}
      <Box mb={6}>
        <Text fontWeight="semibold" mb={2}>Mis abonos</Text>
        {loadingAbonos ? (
          <Stack>
            <Skeleton height="70px" rounded="md" />
            <Skeleton height="70px" rounded="md" />
          </Stack>
        ) : !misAbonos.length ? (
          <Text color={muted}>No tenés abonos.</Text>
        ) : (
          <VStack align="stretch" spacing={3}>
            {misAbonos.map((a) => {
              const elegible = (a.ventana_renovacion === true) && !a.renovado && a.estado_vigencia === "activo";
              return (
                <Box
                  key={a.id}
                  p={3}
                  bg={card.bg}
                  rounded="md"
                  borderWidth="1px"
                  borderColor={input.border}
                >
                  <HStack justify="space-between" align="start">
                    <Box>
                      <Text fontWeight="semibold">
                        {DIAS.find(d => d.value === Number(a.dia_semana))?.label} · {fmtHora(a.hora)} hs
                      </Text>
                      <Text fontSize="sm" color={muted}>
                        {String(a.mes).padStart(2, "0")}/{a.anio} · {a.sede_nombre || "Sede"} · {a.prestador_nombre || "Profesor"}
                      </Text>
                      <HStack mt={2} spacing={2} flexWrap="wrap" rowGap={2}>
                        <Badge colorScheme={a.estado_vigencia === "activo" ? "green" : "gray"}>
                          {a.estado_vigencia}
                        </Badge>
                        {a.renovado ? (
                          <Badge colorScheme="purple" variant="subtle">renovado</Badge>
                        ) : (
                          <Badge variant="outline">vence {a.vence_el || "—"}</Badge>
                        )}
                        <Badge variant="outline">{(a?.tipo_clase_codigo || "").toUpperCase()}</Badge>
                      </HStack>
                    </Box>
                    <Button
                      size="sm"
                      variant={elegible ? "primary" : "secondary"}
                      isDisabled={!elegible}
                      onClick={() => abrirRenovarAbono(a)}
                    >
                      Renovar
                    </Button>
                  </HStack>
                </Box>
              );
            })}
          </VStack>
        )}
      </Box>

      <Divider my={4} />

      <HStack justify="space-between" mb={4} align="end">
        <Text fontSize="2xl" fontWeight="bold">Reservar Abono Mensual</Text>
      </HStack>

      {/* === Reserva NUEVA === */}
      <VStack align="stretch" spacing={3}>
        <Stack
          direction={{ base: "column", md: "row" }}
          spacing={4}
          align={{ base: "stretch", md: "end" }}
          mb={6}
          w="100%"
        >
          {/* Sede */}
          <FormControl flex={1} minW={0}>
            <FormLabel color={muted}>Sede</FormLabel>
            <Select
              value={sedeId}
              placeholder="Seleccioná"
              onChange={(e) => {
                setSedeId(e.target.value);
                setProfesorId(""); setDiaSemana(""); setTipoAbono(""); setHoraFiltro("");
              }}
              bg={input.bg}
              borderColor={input.border}
              size={{ base: "md", md: "sm" }}
              w="100%"
              rounded="md"
            >
              {sedes.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nombre || s.nombre_publico || `Sede ${s.id}`}
                </option>
              ))}
            </Select>
          </FormControl>

          {/* Profesor */}
          <FormControl flex={1} minW={0} isDisabled={!sedeId}>
            <FormLabel color={muted}>Profesor</FormLabel>
            <Select
              value={profesorId}
              placeholder="Seleccioná"
              onChange={(e) => {
                setProfesorId(e.target.value);
                setDiaSemana(""); // Limpiar día al cambiar profesor
              }}
              bg={input.bg}
              borderColor={input.border}
              size={{ base: "md", md: "sm" }}
              w="100%"
              rounded="md"
            >
              {profesores.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nombre || p.email || `Profe ${p.id}`}
                </option>
              ))}
            </Select>
          </FormControl>

          {/* Día de la semana */}
          <FormControl flex={1} minW={0} isDisabled={!profesorId}>
            <FormLabel color={muted}>
              Día de la semana
              {profesorId && (
                <Text as="span" fontSize="xs" color="gray.500" ml={1}>
                  (solo días disponibles)
                </Text>
              )}
            </FormLabel>
            <Select
              value={diaSemana}
              placeholder="Seleccioná"
              onChange={(e) => setDiaSemana(e.target.value)}
              bg={input.bg}
              borderColor={input.border}
              size={{ base: "md", md: "sm" }}
              w="100%"
              rounded="md"
            >
              {DIAS.filter(d => diasDisponibles.includes(d.value)).map((d) => (
                <option key={d.value} value={d.value}>
                  {d.label}
                </option>
              ))}
            </Select>
          </FormControl>

          {/* Tipo de abono */}
          <FormControl flex={1} minW={0} isDisabled={!profesorId}>
            <FormLabel color={muted}>Tipo de abono</FormLabel>
            <Select
              value={tipoAbono}
              placeholder="Seleccioná"
              onChange={(e) => setTipoAbono(e.target.value)}
              bg={input.bg}
              borderColor={input.border}
              size={{ base: "md", md: "sm" }}
              w="100%"
              rounded="md"
            >
              {ABONO_OPCIONES.map((op) => (
                <option key={op.codigo} value={op.codigo}>
                  {op.nombre}
                </option>
              ))}
            </Select>
          </FormControl>

          {/* Hora (opcional) */}
          <FormControl flex={1} minW={0} isDisabled={diaSemana === ""}>
            <FormLabel color={muted}>
              Hora (opcional)
            </FormLabel>
            <Select
              value={horaFiltro}
              onChange={(e) => setHoraFiltro(e.target.value)}
              bg={input.bg}
              borderColor={input.border}
              size={{ base: "md", md: "sm" }}
              w="100%"
              rounded="md"
            >
              <option value="">Todas</option>
              {Array.from({ length: 15 }).map((_, i) => {
                const h = (8 + i).toString().padStart(2, "0") + ":00:00";
                return (
                  <option key={h} value={h}>
                    {h.slice(0, 5)}
                  </option>
                );
              })}
            </Select>
          </FormControl>
        </Stack>

        <Divider my={2} />


        <Box>
          <Text fontWeight="semibold" mb={2}>
            Abonos libres {loadingDisponibles ? "— cargando..." : ""}
          </Text>
          {(sedeId && profesorId && diaSemana !== "" && !tipoAbono) && (
            <Text color={muted} mb={2}>Elegí un tipo de abono para ver disponibilidad.</Text>
          )}
          {!loadingDisponibles && abonosLibres.length === 0 && (sedeId && profesorId && diaSemana !== "" && tipoAbono && tipoAbono !== "") ? (
            <Alert status="info" borderRadius="md">
              <AlertIcon />
              <Box>
                <Text fontWeight="semibold">No hay abonos disponibles</Text>
                <Text fontSize="sm">
                  No hay turnos disponibles para {DIAS.find(d => d.value === Number(diaSemana))?.label} en el mes actual. 
                  Probá con otro día de la semana o esperá al próximo mes.
                </Text>
              </Box>
            </Alert>
          ) : null}

          <VStack align="stretch" spacing={3}>
            {/* Para ambos tipos de abono, mostrar todos los disponibles */}
            {abonosLibres.map((item, idx) => {
              const codigo = item?.tipo_clase?.codigo;
              const pAbono = precioAbonoPorCodigo[codigo];
              
              // Calcular precio dinámico basado en turnos del mes
              const calcularPrecioDinamico = () => {
                console.log('🔍 DEBUG calcularPrecioDinamico - INICIO:', {
                  tipoAbono,
                  item_hora: item?.hora,
                  diaSemana,
                  profesorId,
                  sedeId
                });
                
                if (tipoAbono === "personalizado") {
                  console.log('🔍 DEBUG calcularPrecioDinamico - PERSONALIZADO');
                  return calcularMontoPersonalizado();
                }
                
                // Para abonos normales, buscar el tipo de clase correspondiente
                const tipoClase = tiposClase.find(tc => tc.codigo === tipoAbono);
                console.log('🔍 DEBUG calcularPrecioDinamico - TIPO CLASE:', {
                  tipoAbono,
                  tiposClaseDisponibles: tiposClase.map(tc => ({ codigo: tc.codigo, precio: tc.precio })),
                  tipoClaseEncontrada: tipoClase ? { codigo: tipoClase.codigo, precio: tipoClase.precio } : null
                });
                
                if (tipoClase) {
                  // Calcular turnos del mes para el día seleccionado
                  const turnosDelMes = calcularMaximoTurnos();
                  const precio = Number(tipoClase.precio) * turnosDelMes;
                  
                  console.log('🔍 DEBUG calcularPrecioDinamico - CALCULADO:', {
                    tipoAbono,
                    tipoClase: tipoClase.codigo,
                    precioTipoClase: tipoClase.precio,
                    turnosDelMes,
                    precioFinal: precio,
                    diaSemana,
                    profesorId
                  });
                  
                  return precio;
                }
                
                console.log('🔍 DEBUG calcularPrecioDinamico - NO TIPO CLASE:', {
                  tipoAbono,
                  tiposClase: tiposClase.length
                });
                return 0;
              };
              
              const montoMostrar = calcularPrecioDinamico();
              
              console.log('🚨 DEBUG Badge precio CRÍTICO:', {
                tipoAbono,
                montoMostrar,
                item_hora: item?.hora,
                tiposClase: tiposClase.length,
                calcularMaximoTurnos: calcularMaximoTurnos(),
                sedeId,
                profesorId,
                diaSemana
              });

              return (
                <Box
                  key={`${item?.hora || "hora"}-${idx}`}
                  p={3}
                  bg={card.bg}
                  rounded="md"
                  borderWidth="1px"
                  borderColor={input.border}
                  _hover={{ boxShadow: "lg", cursor: "pointer", opacity: 0.95 }}
                  onClick={() => abrirPagoReservaNueva(item)}
                >
                  <HStack justify="space-between" align="center">
                    <Box>
                      <Text fontWeight="semibold">
                        {DIAS.find(d => String(d.value) === String(diaSemana))?.label} · {fmtHora(item?.hora)} hs
                      </Text>

                      {/* SUBLINE igual que en "Mis abonos": MM/AAAA · Sede · Profesor */}
                      <Text fontSize="sm" color={muted}>
                        {String(mesActual).padStart(2, "0")}/{anioActual}
                        {" · "}
                        {sedeSel?.nombre || sedeSel?.nombre_publico || `Sede ${sedeId}`}
                        {" · "}
                        {profSel?.nombre_publico || profSel?.nombre || profSel?.email || `Profe ${profesorId}`}
                      </Text>

                      <HStack mt={2} spacing={2}>
                        {tipoAbono === "personalizado" ? (
                          <Badge colorScheme="purple">
                            {mostrarConfiguracionPersonalizada(item?.configuracion_personalizada, tiposClase)}
                          </Badge>
                        ) : (
                          <>
                        <Badge variant="outline">
                          {LABELS[tipoAbono] || "Tipo"}
                        </Badge>
                        <Badge colorScheme="green">
                              ${montoMostrar.toLocaleString("es-AR")}
                        </Badge>
                          </>
                        )}
                      </HStack>
                    </Box>

                    <Button 
                      variant="primary"
                    >
                      Seleccionar
                    </Button>
                  </HStack>

                </Box>
              );
            })}
          </VStack>
        </Box>
      </VStack>

      {/* Modal de configuración personalizada */}
      <Modal
        isOpen={configDisc.isOpen}
        onClose={configDisc.onClose}
        isCentered
        size="lg"
      >
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Configurar Abono Personalizado</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack align="stretch" spacing={4}>
              <Box p={4} bg="blue.50" rounded="md">
                <Text fontWeight="semibold" mb={2}>Resumen del Abono</Text>
                {modoRenovacion ? (
                  // Para renovaciones, mostrar información del abono existente
                  <>
                    <Text fontSize="sm" color="gray.600">
                      <strong>Día:</strong> {DIAS.find(d => d.value === Number(seleccion?.dia_semana))?.label}
                    </Text>
                    <Text fontSize="sm" color="gray.600">
                      <strong>Hora:</strong> {seleccion?.hora ? fmtHora(seleccion.hora) : "Todas las horas"}
                    </Text>
                    <Text fontSize="sm" color="gray.600">
                      <strong>Profesor:</strong> {(() => {
                        console.log('DEBUG profesor:', { 
                          seleccion_prestador: seleccion?.prestador, 
                          profesores: profesores.length,
                          profesor_encontrado: profesores.find(p => String(p.id) === String(seleccion?.prestador))
                        });
                        return profesores.find(p => String(p.id) === String(seleccion?.prestador))?.nombre || "Cargando...";
                      })()}
                    </Text>
                    <Text fontSize="sm" color="gray.600">
                      <strong>Mes siguiente:</strong> {seleccion?.mes && seleccion?.anio ? `${String(seleccion.mes).padStart(2, "0")}/${seleccion.anio}` : "N/A"}
                    </Text>
                  </>
                ) : (
                  // Para abonos nuevos, mostrar información del filtro actual
                  <>
                    <Text fontSize="sm" color="gray.600">
                      <strong>Día:</strong> {DIAS.find(d => d.value === Number(diaSemana))?.label}
                    </Text>
                    <Text fontSize="sm" color="gray.600">
                      <strong>Hora:</strong> {abonoParaConfigurar?.hora ? fmtHora(abonoParaConfigurar.hora) : (horaFiltro ? horaFiltro.slice(0, 5) : "Todas las horas")}
                    </Text>
                    <Text fontSize="sm" color="gray.600">
                      <strong>Profesor:</strong> {profesores.find(p => String(p.id) === String(profesorId))?.nombre}
                    </Text>
                    <Text fontSize="sm" color="gray.600">
                      <strong>Turnos disponibles:</strong> {calcularMaximoTurnos()}
                    </Text>
                  </>
                )}
              </Box>

              <Box>
                <Text fontWeight="semibold" mb={3}>Configuración de Clases</Text>
                {modoRenovacion ? (
                  // Para renovaciones, mostrar turnos del mes siguiente
                  <VStack align="stretch" spacing={3}>
                    <Text fontSize="sm" color="gray.600" mb={3}>
                      El mes siguiente tiene {calcularTurnosDelMes(seleccion?.anio, seleccion?.mes, seleccion?.dia_semana, false)} {DIAS.find(d => d.value === Number(seleccion?.dia_semana))?.label.toLowerCase()}. 
                      Seleccioná qué tipo de clase querés tener para cada turno:
                    </Text>
                    {Array.from({ length: calcularTurnosDelMes(seleccion?.anio, seleccion?.mes, seleccion?.dia_semana, false) }, (_, index) => (
                      <HStack key={index} spacing={3} align="end">
                        <FormControl flex={2}>
                          <FormLabel fontSize="sm">Turno {index + 1} - Tipo de Clase</FormLabel>
                          <Select
                            value={configuracionPersonalizada[index]?.tipo_clase_id || ""}
                            onChange={(e) => {
                              const newConfig = [...configuracionPersonalizada];
                              if (!newConfig[index]) {
                                newConfig[index] = { tipo_clase_id: Number(e.target.value), cantidad: 1 };
                              } else {
                                newConfig[index].tipo_clase_id = Number(e.target.value);
                              }
                              setConfiguracionPersonalizada(newConfig);
                            }}
                          >
                            <option value="">Seleccionar tipo</option>
                            {(() => {
                              console.log('DEBUG tiposClase en dropdown:', { 
                                tiposClase: tiposClase.length,
                                tiposClase_data: tiposClase 
                              });
                              return tiposClase.map(tc => (
                                <option key={tc.id} value={tc.id}>
                                  {LABELS[tc.codigo]} - ${Number(tc.precio).toLocaleString("es-AR")}
                                </option>
                              ));
                            })()}
                          </Select>
                        </FormControl>
                      </HStack>
                    ))}
                  </VStack>
                ) : configuracionPersonalizada.length === 0 ? (
                  <Text color="gray.500" textAlign="center" py={4}>
                    No hay tipos de clase configurados. Agregá al menos uno para continuar.
                  </Text>
                ) : (
                  <VStack align="stretch" spacing={3}>
                    {configuracionPersonalizada.map((config, index) => {
                      const tipoClase = tiposClase.find(tc => tc.id === config.tipo_clase_id);
                      return (
                        <HStack key={index} spacing={3} align="end">
                          <FormControl flex={2}>
                            <FormLabel fontSize="sm">Turno {index + 1} - Tipo de Clase</FormLabel>
                            <Select
                              value={config.tipo_clase_id}
                              onChange={(e) => actualizarTipoClase(index, 'tipo_clase_id', Number(e.target.value))}
                              bg={input.bg}
                              borderColor={input.border}
                              size="sm"
                            >
                              {tiposClase.map(tc => (
                                <option key={tc.id} value={tc.id}>
                                  {tc.nombre || LABELS[tc.codigo]} - ${Number(tc.precio).toLocaleString("es-AR")}
                                </option>
                              ))}
                            </Select>
                          </FormControl>
                          
                          <Box flex={1}>
                            <Text fontSize="sm" color="gray.600">Subtotal</Text>
                            <Text fontWeight="semibold">
                              ${(Number(tipoClase?.precio || 0) * config.cantidad).toLocaleString("es-AR")}
                            </Text>
                          </Box>
                          
                        </HStack>
                      );
                    })}
                    
                    <Divider />
                    
                    <HStack justify="space-between" align="center">
                      <VStack align="start" spacing={1}>
                        <Text fontWeight="bold" fontSize="lg">Total del Abono:</Text>
                        {calcularTurnosAsignados() > calcularMaximoTurnos() && (
                          <Text fontSize="sm" color="red.500">
                            ⚠️ Excede el límite de turnos disponibles
                          </Text>
                        )}
                      </VStack>
                      <VStack align="end" spacing={1}>
                        <Text fontWeight="bold" fontSize="lg" color={calcularTurnosAsignados() > calcularMaximoTurnos() ? "red.500" : "green.500"}>
                          ${calcularMontoPersonalizado().toLocaleString("es-AR")}
                        </Text>
                        <Text fontSize="sm" color="gray.600">
                          {configuracionPersonalizada.reduce((total, config) => total + config.cantidad, 0)} de {calcularMaximoTurnos()} turnos
                        </Text>
                      </VStack>
                    </HStack>
                  </VStack>
                )}
              </Box>

              {/* Mostrar monto total para renovaciones */}
              {modoRenovacion && (
                <Box p={3} bg="green.50" rounded="md" border="1px solid" borderColor="green.200">
                  <HStack justify="space-between" align="center">
                    <Text fontWeight="semibold" color="green.700">
                      Total del Abono:
                    </Text>
                    <Text fontWeight="bold" fontSize="lg" color="green.600">
                      ${configuracionPersonalizada.reduce((total, config) => {
                        const tipoClase = tiposClase.find(tc => tc.id === config.tipo_clase_id);
                        return total + (Number(tipoClase?.precio || 0) * config.cantidad);
                      }, 0).toLocaleString("es-AR")}
                    </Text>
                  </HStack>
                </Box>
              )}
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" onClick={configDisc.onClose} mr={3}>
              Cancelar
            </Button>
            <Button
              colorScheme="blue"
              onClick={procederAlPago}
              isDisabled={
                modoRenovacion 
                  ? configuracionPersonalizada.some(config => !config.tipo_clase_id)
                  : configuracionPersonalizada.length === 0 ||
                    calcularTurnosAsignados() > calcularMaximoTurnos()
              }
            >
              Proceder al Pago
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Modal de pago */}
      {modalIsRenderable ? (
        <ReservaPagoModalAbono
          isOpen={pagoDisc.isOpen}
          onClose={pagoDisc.onClose}
          alias={seleccion?.alias}
          cbuCvu={seleccion?.cbu_cvu}
          turno={
            seleccion
              ? { fecha: `Mes ${String(seleccion.mes).padStart(2,"0")}/${seleccion.anio}`, hora: seleccion.hora }
              : null
          }
          tipoClase={seleccion?.tipo_clase || null}
          precioAbono={seleccion?.precio_abono ?? 0}
          precioUnitario={seleccion?.precio_unitario ?? 0}
          configuracionPersonalizada={seleccion?.configuracion_personalizada}
          tiposClase={tiposClase}
          modoRenovacion={modoRenovacion}
          onPersonalizar={() => {
            console.log('DEBUG: onPersonalizar llamado');
            console.log('DEBUG: modoRenovacion:', modoRenovacion);
            console.log('DEBUG: configDisc:', configDisc);
            
            // Para renovaciones, abrir modal de configuración personalizada
            if (modoRenovacion) {
              console.log('DEBUG: Abriendo modal de configuración');
              
              console.log('DEBUG antes de abrir modal:', {
                profesores: profesores.length,
                tiposClase: tiposClase.length,
                seleccion
              });
              
              // Cargar datos necesarios para el modal de configuración
              if (api && seleccion?.sede) {
                // Cargar profesores para la sede del abono
                api.get(`turnos/prestadores/?lugar_id=${seleccion.sede}`)
                  .then(res => {
                    const data = res?.data?.results ?? res?.data ?? [];
                    setProfesores(Array.isArray(data) ? data : []);
                  })
                  .catch(e => {
                    console.error("Error cargando profesores:", e);
                    setProfesores([]);
                  });
                
                // Cargar tipos de clase para la sede del abono
                api.get(`padel/tipos-clase/?sede_id=${seleccion.sede}`)
                  .then(res => {
                    const data = res?.data?.results ?? res?.data ?? [];
                    const tiposCargados = Array.isArray(data) ? data : [];
                    setTiposClase(tiposCargados);
                    
                    // Inicializar configuración personalizada con TODOS los turnos del mes (obligatorio configurar cada uno)
                    const turnosDelMes = calcularTurnosDelMes(seleccion?.anio, seleccion?.mes, seleccion?.dia_semana, false);
                    const configuracionInicial = Array.from({ length: turnosDelMes }, (_, index) => ({
                      tipo_clase_id: tiposCargados.length > 0 ? tiposCargados[0].id : null,
                      cantidad: 1
                    }));
                    setConfiguracionPersonalizada(configuracionInicial);
                  })
                  .catch(e => {
                    console.error("Error cargando tipos de clase:", e);
                    setTiposClase([]);
                    // Inicializar con array vacío si no se pueden cargar los tipos
                    const turnosDelMes = calcularTurnosDelMes(seleccion?.anio, seleccion?.mes, seleccion?.dia_semana, false);
                    const configuracionInicial = Array.from({ length: turnosDelMes }, (_, index) => ({
                      tipo_clase_id: null,
                      cantidad: 1
                    }));
                    setConfiguracionPersonalizada(configuracionInicial);
                  });
              } else if (tiposClase.length === 0 && api && sedeId) {
                // Fallback: cargar tipos de clase con sedeId general
                api.get(`padel/tipos-clase/?sede_id=${sedeId}`)
                  .then(res => {
                    const data = res?.data?.results ?? res?.data ?? [];
                    const tiposCargados = Array.isArray(data) ? data : [];
                    setTiposClase(tiposCargados);
                    
                    // Inicializar configuración personalizada con TODOS los turnos del mes (obligatorio configurar cada uno)
                    const turnosDelMes = calcularTurnosDelMes(seleccion?.anio, seleccion?.mes, seleccion?.dia_semana, false);
                    const configuracionInicial = Array.from({ length: turnosDelMes }, (_, index) => ({
                      tipo_clase_id: tiposCargados.length > 0 ? tiposCargados[0].id : null,
                      cantidad: 1
                    }));
                    setConfiguracionPersonalizada(configuracionInicial);
                  })
                  .catch(() => {
                    setTiposClase([]);
                    // Inicializar con array vacío si no se pueden cargar los tipos
                    const turnosDelMes = calcularTurnosDelMes(seleccion?.anio, seleccion?.mes, seleccion?.dia_semana, false);
                    const configuracionInicial = Array.from({ length: turnosDelMes }, (_, index) => ({
                      tipo_clase_id: null,
                      cantidad: 1
                    }));
                    setConfiguracionPersonalizada(configuracionInicial);
                  });
              } else {
                // Si ya están cargados, inicializar directamente
                const turnosDelMes = calcularTurnosDelMes(seleccion?.anio, seleccion?.mes, seleccion?.dia_semana, false);
                const configuracionInicial = Array.from({ length: turnosDelMes }, (_, index) => ({
                  tipo_clase_id: tiposClase.length > 0 ? tiposClase[0].id : null,
                  cantidad: 1
                }));
                setConfiguracionPersonalizada(configuracionInicial);
              }
              
              configDisc.onOpen();
            } else {
              console.log('DEBUG: No es modo renovación, no se abre modal');
            }
          }}
          archivo={archivo}
          onArchivoChange={setArchivo}
          onRemoveArchivo={() => setArchivo(null)}
          onConfirmar={(ids) => onConfirmarPago(ids)}
          loading={enviando}
          tiempoRestante={configPago?.tiempo_maximo_minutos ? configPago.tiempo_maximo_minutos * 60 : undefined}
          bonificaciones={bonificaciones}
          selectedBonos={selectedBonos}
          setSelectedBonos={setSelectedBonos}
        />
      ) : (
        <Box mt={4} p={4} borderWidth="1px" rounded="md" bg="red.50" color="red.700">
          El componente de pago no se pudo cargar.
        </Box>
      )}
    </Box>
  );
};

export default ReservarAbono;
