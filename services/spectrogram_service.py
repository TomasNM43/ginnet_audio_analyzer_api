"""
Servicio para generación de espectrogramas
"""
import os
import librosa
import librosa.display
import matplotlib
matplotlib.use('Agg')  # Backend no interactivo
import matplotlib.pyplot as plt
import numpy as np
from typing import List, Tuple, Dict

class SpectrogramService:
    """Servicio para generar espectrogramas de audio"""
    
    @staticmethod
    def save_spectrogram(y: np.ndarray, sr: int, start: int, end: int, 
                        start_time: float, end_time: float, output_path: str) -> None:
        """Guarda un espectrograma en el path especificado"""
        plt.figure(figsize=(10, 4))
        D = librosa.amplitude_to_db(np.abs(librosa.stft(y[start:end])), ref=np.max)
        librosa.display.specshow(D, sr=sr, x_axis='time', y_axis='log', cmap='gray')
        plt.colorbar(format='%+2.0f dB')
        plt.title(f'Spectrogram: {int(start_time // 60)}:{int(start_time % 60):02d} - {int(end_time // 60)}:{int(end_time % 60):02d} min')
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
    
    @staticmethod
    def generate_spectrograms_for_file(audio_path: str, file_prefix: str, 
                                      output_dir: str, segment_length: int = 3, 
                                      extra_duration: float = 0.05) -> Dict[str, any]:
        """
        Genera espectrogramas para un archivo de audio completo
        
        Args:
            audio_path: Ruta al archivo de audio
            file_prefix: Prefijo para nombrar los archivos generados
            output_dir: Directorio donde guardar los espectrogramas
            segment_length: Duración de cada segmento en segundos
            extra_duration: Duración extra para evitar cortes
            
        Returns:
            Diccionario con información de los espectrogramas generados
        """
        y, sr = librosa.load(audio_path, sr=None)
        duration = librosa.get_duration(y=y, sr=sr)
        
        os.makedirs(output_dir, exist_ok=True)
        
        spectrograms = []
        i = 0
        while i < duration:
            start_time = i
            end_time = i + segment_length + extra_duration
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)
            
            if end_sample > len(y):
                end_sample = len(y)
                end_time = len(y) / sr
            
            if end_sample > start_sample:
                output_filename = f'{file_prefix}_spectrogram_{int(start_time)}_{int(end_time)}.png'
                output_path = os.path.join(output_dir, output_filename)
                SpectrogramService.save_spectrogram(
                    y[start_sample:end_sample], sr, 0, end_sample - start_sample, 
                    start_time, end_time, output_path
                )
                spectrograms.append({
                    'filename': output_filename,
                    'path': output_path,
                    'start_time': start_time,
                    'end_time': end_time
                })
            
            i += segment_length
        
        return {
            'total_spectrograms': len(spectrograms),
            'duration': duration,
            'segment_length': segment_length,
            'spectrograms': spectrograms
        }
    
    @staticmethod
    def generate_spectrograms_by_time_range(audio_path: str, file_prefix: str,
                                           output_dir: str, start_time: float, 
                                           end_time: float, segment_length: int = 3,
                                           mode: str = "complete", time_jump: float = 3,
                                           extra_duration: float = 0.05) -> Dict[str, any]:
        """
        Genera espectrogramas en un rango de tiempo específico
        
        Args:
            audio_path: Ruta al archivo de audio
            file_prefix: Prefijo para nombrar archivos
            output_dir: Directorio de salida
            start_time: Tiempo inicial en segundos
            end_time: Tiempo final en segundos
            segment_length: Duración de cada segmento
            mode: "complete" o "combined"
            time_jump: Salto de tiempo para modo combinado
            extra_duration: Duración extra
            
        Returns:
            Diccionario con información de los espectrogramas generados
        """
        y, sr = librosa.load(audio_path, sr=None)
        duration = librosa.get_duration(y=y, sr=sr)
        
        # Validar tiempos
        if start_time < 0:
            start_time = 0
        if end_time > duration:
            end_time = duration
        if start_time >= end_time:
            raise ValueError("El tiempo inicial debe ser menor que el tiempo final")
        
        os.makedirs(output_dir, exist_ok=True)
        spectrograms = []
        
        i = start_time
        
        if mode == "complete":
            advance_step = segment_length
        else:  # mode == "combined"
            # Primero cobertura completa
            temp_i = start_time
            while temp_i < end_time:
                segment_start_time = temp_i
                segment_end_time = min(temp_i + segment_length + extra_duration, end_time)
                start_sample = int(segment_start_time * sr)
                end_sample = int(segment_end_time * sr)
                
                if end_sample > len(y):
                    end_sample = len(y)
                    segment_end_time = len(y) / sr
                
                if end_sample > start_sample:
                    output_filename = f'{file_prefix}_complete_spectrogram_{int(segment_start_time)}_{int(segment_end_time)}.png'
                    output_path = os.path.join(output_dir, output_filename)
                    SpectrogramService.save_spectrogram(
                        y[start_sample:end_sample], sr, 0, end_sample - start_sample, 
                        segment_start_time, segment_end_time, output_path
                    )
                    spectrograms.append({
                        'filename': output_filename,
                        'path': output_path,
                        'start_time': segment_start_time,
                        'end_time': segment_end_time,
                        'type': 'complete'
                    })
                
                temp_i += segment_length
            
            advance_step = time_jump
        
        while i < end_time:
            segment_start_time = i
            segment_end_time = min(i + segment_length + extra_duration, end_time)
            start_sample = int(segment_start_time * sr)
            end_sample = int(segment_end_time * sr)
            
            if end_sample > len(y):
                end_sample = len(y)
                segment_end_time = len(y) / sr
            
            if end_sample > start_sample:
                if mode == "combined":
                    if i % segment_length != 0 or i == start_time:
                        prefix = "jump"
                    else:
                        i += advance_step
                        continue
                else:
                    prefix = "range"
                
                output_filename = f'{file_prefix}_{prefix}_spectrogram_{int(segment_start_time)}_{int(segment_end_time)}.png'
                output_path = os.path.join(output_dir, output_filename)
                SpectrogramService.save_spectrogram(
                    y[start_sample:end_sample], sr, 0, end_sample - start_sample, 
                    segment_start_time, segment_end_time, output_path
                )
                spectrograms.append({
                    'filename': output_filename,
                    'path': output_path,
                    'start_time': segment_start_time,
                    'end_time': segment_end_time,
                    'type': prefix
                })
            
            i += advance_step
        
        return {
            'total_spectrograms': len(spectrograms),
            'duration': duration,
            'segment_length': segment_length,
            'start_time': start_time,
            'end_time': end_time,
            'mode': mode,
            'spectrograms': spectrograms
        }
    
    @staticmethod
    def generate_spectrograms_by_jumps(audio_path: str, file_prefix: str,
                                      output_dir: str, time_jump: float = 3,
                                      segment_length: int = 3, 
                                      extra_duration: float = 0.05) -> Dict[str, any]:
        """
        Genera espectrogramas con saltos de tiempo específicos
        
        Args:
            audio_path: Ruta al archivo de audio
            file_prefix: Prefijo para nombrar archivos
            output_dir: Directorio de salida
            time_jump: Salto de tiempo en segundos
            segment_length: Duración de cada segmento
            extra_duration: Duración extra
            
        Returns:
            Diccionario con información de los espectrogramas generados
        """
        y, sr = librosa.load(audio_path, sr=None)
        duration = librosa.get_duration(y=y, sr=sr)
        
        os.makedirs(output_dir, exist_ok=True)
        spectrograms = []
        
        i = 0
        while i < duration:
            segment_start_time = i
            segment_end_time = min(i + segment_length + extra_duration, duration)
            start_sample = int(segment_start_time * sr)
            end_sample = int(segment_end_time * sr)
            
            if end_sample > len(y):
                end_sample = len(y)
                segment_end_time = len(y) / sr
            
            if end_sample > start_sample:
                output_filename = f'{file_prefix}_jump_spectrogram_{int(segment_start_time)}_{int(segment_end_time)}.png'
                output_path = os.path.join(output_dir, output_filename)
                SpectrogramService.save_spectrogram(
                    y[start_sample:end_sample], sr, 0, end_sample - start_sample, 
                    segment_start_time, segment_end_time, output_path
                )
                spectrograms.append({
                    'filename': output_filename,
                    'path': output_path,
                    'start_time': segment_start_time,
                    'end_time': segment_end_time
                })
            
            i += time_jump
        
        return {
            'total_spectrograms': len(spectrograms),
            'duration': duration,
            'time_jump': time_jump,
            'segment_length': segment_length,
            'spectrograms': spectrograms
        }
