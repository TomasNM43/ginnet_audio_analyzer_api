"""
Servicio para generación de reportes
"""
import os
import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from docx import Document
from docx.shared import Inches
from PIL import Image
from typing import Dict, List

class ReportService:
    """Servicio para generar reportes consolidados"""
    
    @staticmethod
    def create_summary_chart(detections_by_file: Dict, output_path: str = 'summary_chart.png') -> str:
        """
        Crea un gráfico resumen de detecciones
        
        Args:
            detections_by_file: Diccionario con detecciones por archivo
            output_path: Ruta donde guardar el gráfico
            
        Returns:
            Ruta al archivo del gráfico generado
        """
        plt.figure(figsize=(15, 8))
        
        file_names = list(detections_by_file.keys())
        y_positions = range(len(file_names))
        
        colors = {'detection': 'red', 'no_detection': 'green'}
        
        for i, file_name in enumerate(file_names):
            segments = detections_by_file[file_name]['segments']
            
            for segment in segments:
                start = segment['start']
                end = segment['end']
                color = colors['detection'] if segment['has_detection'] else colors['no_detection']
                
                plt.barh(i, end - start, left=start, height=0.6,
                       color=color, alpha=0.7, edgecolor='black', linewidth=0.5)
        
        plt.yticks(y_positions, file_names)
        plt.xlabel('Tiempo (segundos)')
        plt.ylabel('Archivos de Audio')
        plt.title('Resumen de Detecciones por Archivo de Audio')
        
        legend_elements = [
            Patch(facecolor='red', alpha=0.7, label='Corte Detectado'),
            Patch(facecolor='green', alpha=0.7, label='Sin Corte')
        ]
        plt.legend(handles=legend_elements, loc='upper right')
        
        plt.grid(True, alpha=0.3, axis='x')
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    @staticmethod
    def generate_consolidated_report(detections_by_file: Dict, audio_files: List[str],
                                    output_dir: str = '.') -> Dict[str, any]:
        """
        Genera un reporte consolidado en formato Word
        
        Args:
            detections_by_file: Diccionario con detecciones por archivo
            audio_files: Lista de archivos de audio procesados
            output_dir: Directorio donde guardar el reporte
            
        Returns:
            Diccionario con información del reporte generado
        """
        doc = Document()
        doc.add_heading('Reporte Consolidado de Análisis de Audio', level=1)
        
        # Información general
        doc.add_heading('Información General', level=2)
        doc.add_paragraph(f'Fecha de análisis: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")}')
        doc.add_paragraph(f'Número de archivos analizados: {len(audio_files)}')
        
        # Lista de archivos procesados
        doc.add_heading('Archivos Procesados', level=2)
        for i, audio_file in enumerate(audio_files, 1):
            file_name = os.path.basename(audio_file) if isinstance(audio_file, str) else audio_file
            doc.add_paragraph(f'{i}. {file_name}')
        
        # Crear y agregar gráfico resumen
        chart_path = os.path.join(output_dir, 'temp_summary_chart.png')
        ReportService.create_summary_chart(detections_by_file, chart_path)
        
        doc.add_heading('Gráfico Resumen de Detecciones', level=2)
        doc.add_paragraph('El siguiente gráfico muestra un resumen de las detecciones encontradas en cada archivo de audio:')
        
        try:
            img = Image.open(chart_path)
            img.thumbnail((Inches(6.0 * 96), Inches(4.0 * 96)))
            temp_chart_resized = os.path.join(output_dir, 'temp_chart_resized.png')
            img.save(temp_chart_resized)
            doc.add_picture(temp_chart_resized, width=Inches(6.0))
            
            if os.path.exists(temp_chart_resized):
                os.remove(temp_chart_resized)
        except Exception as e:
            doc.add_paragraph(f'Error al insertar gráfico: {e}')
        
        # Resumen estadístico
        doc.add_heading('Resumen Estadístico', level=2)
        total_segments = 0
        total_detections = 0
        
        for file_prefix, data in detections_by_file.items():
            segments_count = len(data['segments'])
            detections_count = len(data['detections'])
            total_segments += segments_count
            total_detections += detections_count
            
            detection_percentage = (detections_count / segments_count * 100) if segments_count > 0 else 0
            doc.add_paragraph(f'• {file_prefix}: {detections_count}/{segments_count} segmentos con detección ({detection_percentage:.1f}%)')
        
        overall_percentage = (total_detections / total_segments * 100) if total_segments > 0 else 0
        doc.add_paragraph(f'\nResumen general: {total_detections}/{total_segments} segmentos con detección ({overall_percentage:.1f}%)')
        
        # Guardar documento
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_name = f'Reporte_Consolidado_{timestamp}.docx'
        report_path = os.path.join(output_dir, report_name)
        doc.save(report_path)
        
        # Limpiar archivos temporales
        if os.path.exists(chart_path):
            os.remove(chart_path)
        
        return {
            'report_name': report_name,
            'report_path': report_path,
            'total_segments': total_segments,
            'total_detections': total_detections,
            'overall_percentage': overall_percentage,
            'timestamp': timestamp
        }
    
    @staticmethod
    def generate_transcription_report(transcriptions: List[Dict], output_dir: str = '.') -> Dict[str, any]:
        """
        Genera un reporte de transcripciones en formato TXT
        
        Args:
            transcriptions: Lista de diccionarios con transcripciones
            output_dir: Directorio donde guardar el reporte
            
        Returns:
            Diccionario con información del reporte generado
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f'Transcripcion_{timestamp}.txt'
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("TRANSCRIPCIÓN DE ARCHIVOS DE AUDIO\n")
            f.write("=" * 50 + "\n")
            f.write(f"Fecha: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Total de archivos: {len(transcriptions)}\n\n")
            
            for trans in transcriptions:
                f.write(f"\n{'='*60}\n")
                f.write(f"ARCHIVO {trans['index']}: {trans['file']}\n")
                f.write(f"{'='*60}\n")
                f.write(f"Duración: {trans['duration']}\n")
                f.write(f"Ruta: {trans['path']}\n\n")
                f.write(f"Método de transcripción: {trans['method']}\n")
                f.write(f"TRANSCRIPCIÓN:\n")
                f.write("-" * 40 + "\n")
                f.write(f"{trans['transcription']}\n")
                f.write("-" * 40 + "\n")
                
                if trans['transcription'] and trans['transcription'].startswith('[Error'):
                    f.write("\nCONSEJOS PARA RESOLVER ERRORES:\n")
                    f.write("• Verifique que el archivo de audio no esté dañado\n")
                    f.write("• Asegúrese de tener conexión estable a internet\n")
                    f.write("• Para archivos muy largos, el sistema los segmenta automáticamente\n")
                    f.write("• Pruebe con un archivo más corto o de mejor calidad\n\n")
        
        return {
            'report_name': output_filename,
            'report_path': output_path,
            'total_files': len(transcriptions),
            'timestamp': timestamp
        }
