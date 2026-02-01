import { useState, useEffect } from 'react';

/**
 * Hook para detectar el tipo de dispositivo
 * PC: ≥1024px, Tablet: 600-1023px, Mobile: <600px
 */
export const useDeviceDetection = () => {
  const [deviceType, setDeviceType] = useState('desktop');
  
  useEffect(() => {
    const detectDevice = () => {
      const width = window.innerWidth;
      
      if (width >= 1024) {
        setDeviceType('desktop');
      } else if (width >= 600) {
        setDeviceType('tablet');
      } else {
        setDeviceType('mobile');
      }
    };
    
    // Detectar al cargar
    detectDevice();
    
    // Escuchar cambios de tamaño
    window.addEventListener('resize', detectDevice);
    
    return () => window.removeEventListener('resize', detectDevice);
  }, []);
  
  return {
    deviceType,
    isDesktop: deviceType === 'desktop',
    isTablet: deviceType === 'tablet',
    isMobile: deviceType === 'mobile',
    isResponsive: deviceType === 'tablet' || deviceType === 'mobile'
  };
};
