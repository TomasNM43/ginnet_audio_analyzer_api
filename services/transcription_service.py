"""
Servicio para transcripción de audio
"""
import os
import tempfile
import librosa
import speech_recognition as sr
from pydub import AudioSegment
import soundfile as sf
from typing import Dict, Tuple, Optional

class TranscriptionService:
    """Servicio para transcribir archivos de audio"""
    
    @staticmethod
    def convert_to_wav(audio_path: str) -> Optional[str]:
        """
        Convierte cualquier formato de audio a WAV temporal
        
        Args:
            audio_path: Ruta al archivo de audio
            
        Returns:
            Ruta al archivo WAV temporal o None si hay error
        """
        try:
            if audio_path.lower().endswith('.wav'):
                return audio_path
            
            audio = AudioSegment.from_file(audio_path)
            temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            audio.export(temp_wav.name, format='wav')
            temp_wav.close()
            
            return temp_wav.name
        except Exception as e:
            print(f"Error convirtiendo audio {audio_path}: {e}")
            return None
    
    @staticmethod
    def transcribe_by_segments(wav_path: str, recognizer: sr.Recognizer, 
                              language: str = 'es-ES', 
                              segment_length: int = 30) -> Tuple[str, str]:
        """
        Transcribe archivos largos dividiéndolos en segmentos
        
        Args:
            wav_path: Ruta al archivo WAV
            recognizer: Objeto recognizer configurado
            language: Código de idioma
            segment_length: Duración de cada segmento
            
        Returns:
            Tupla (transcripción, método usado)
        """
        try:
            y, sr_rate = librosa.load(wav_path, sr=None)
            duration = librosa.get_duration(y=y, sr=sr_rate)
            
            if duration <= segment_length:
                with sr.AudioFile(wav_path) as source:
                    audio_data = recognizer.record(source)
                    return recognizer.recognize_google(audio_data, language=language), "Google (archivo completo)"
            
            segments_text = []
            for i in range(0, int(duration), segment_length):
                start_time = i
                end_time = min(i + segment_length, duration)
                
                start_sample = int(start_time * sr_rate)
                end_sample = int(end_time * sr_rate)
                segment = y[start_sample:end_sample]
                
                temp_segment = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                temp_segment.close()
                sf.write(temp_segment.name, segment, sr_rate)
                
                try:
                    with sr.AudioFile(temp_segment.name) as source:
                        recognizer.adjust_for_ambient_noise(source, duration=0.5)
                        audio_data = recognizer.record(source)
                        
                    try:
                        segment_text = recognizer.recognize_google(audio_data, language=language)
                        segments_text.append(f"[{int(start_time//60)}:{int(start_time%60):02d}-{int(end_time//60)}:{int(end_time%60):02d}] {segment_text}")
                    except sr.UnknownValueError:
                        segments_text.append(f"[{int(start_time//60)}:{int(start_time%60):02d}-{int(end_time//60)}:{int(end_time%60):02d}] [Inaudible]")
                    except sr.RequestError:
                        segments_text.append(f"[{int(start_time//60)}:{int(start_time%60):02d}-{int(end_time//60)}:{int(end_time%60):02d}] [Error de API]")
                        
                finally:
                    try:
                        os.unlink(temp_segment.name)
                    except:
                        pass
            
            return "\n".join(segments_text), "Google (por segmentos)"
            
        except Exception as e:
            raise Exception(f"Error en transcripción por segmentos: {e}")
    
    @staticmethod
    def transcribe_audio(audio_path: str, language: str = 'es-ES', 
                        max_duration: int = 300) -> Tuple[str, str]:
        """
        Transcribe un archivo de audio completo usando varios métodos
        
        Args:
            audio_path: Ruta al archivo de audio
            language: Código de idioma (ej: 'es-ES', 'en-US')
            max_duration: Duración máxima permitida en segundos
            
        Returns:
            Tupla (transcripción, método usado)
        """
        recognizer = sr.Recognizer()
        
        # Configurar el reconocedor
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8
        recognizer.operation_timeout = None
        recognizer.phrase_threshold = 0.3
        recognizer.non_speaking_duration = 0.8
        
        wav_path = TranscriptionService.convert_to_wav(audio_path)
        if wav_path is None:
            return None, "Error al convertir el archivo de audio"
        
        try:
            # Verificar duración
            try:
                y, sr_rate = librosa.load(wav_path, sr=None)
                duration = librosa.get_duration(y=y, sr=sr_rate)
                
                if duration > max_duration:
                    return (f"[Archivo demasiado largo ({duration:.1f}s). "
                           f"Máximo permitido: {max_duration}s. Use la función de segmentación.]",
                           "Archivo muy largo")
            except:
                pass
            
            # Cargar archivo de audio
            with sr.AudioFile(wav_path) as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
                audio_data = recognizer.record(source)
            
            # Método 1: Google Speech Recognition
            try:
                text = recognizer.recognize_google(
                    audio_data, 
                    language=language,
                    show_all=False
                )
                return text, "Google Speech Recognition"
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                print(f"Error Google API: {e}")
            
            # Método 2: Reconocimiento por segmentos
            try:
                return TranscriptionService.transcribe_by_segments(wav_path, recognizer, language)
            except:
                pass
            
            # Si todos fallan
            return "[No se pudo transcribir el audio con ningún método disponible]", "Error - todos los métodos fallaron"
        
        except Exception as e:
            return f"[Error procesando archivo: {str(e)}]", "Error de procesamiento"
        
        finally:
            if wav_path != audio_path and os.path.exists(wav_path):
                try:
                    os.unlink(wav_path)
                except:
                    pass
    
    @staticmethod
    def transcribe_multiple_files(audio_paths: list, language: str = 'es-ES') -> Dict[str, any]:
        """
        Transcribe múltiples archivos de audio
        
        Args:
            audio_paths: Lista de rutas a archivos de audio
            language: Código de idioma
            
        Returns:
            Diccionario con las transcripciones
        """
        transcriptions = []
        
        for i, audio_path in enumerate(audio_paths, 1):
            file_name = os.path.basename(audio_path)
            
            # Obtener duración
            try:
                y, sr_rate = librosa.load(audio_path, sr=None)
                duration = librosa.get_duration(y=y, sr=sr_rate)
                duration_str = f"{int(duration // 60)}:{int(duration % 60):02d}"
            except:
                duration_str = "Desconocida"
            
            # Transcribir
            transcription, method = TranscriptionService.transcribe_audio(audio_path, language=language)
            
            transcriptions.append({
                'file': file_name,
                'path': audio_path,
                'duration': duration_str,
                'transcription': transcription,
                'method': method,
                'index': i
            })
        
        return {
            'total_files': len(audio_paths),
            'language': language,
            'transcriptions': transcriptions
        }
