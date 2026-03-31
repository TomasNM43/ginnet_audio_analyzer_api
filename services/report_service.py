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

# ReportLab imports para PDF
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

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
    def _seconds_to_mmss(seconds: int) -> str:
        """Convierte segundos a formato M:SS (ej. 125 → '2:05')"""
        m, s = divmod(int(seconds), 60)
        return f"{m}:{s:02d}"

    @staticmethod
    def generate_consolidated_report(detections_by_file: Dict, audio_files: List[str],
                                    output_dir: str = '.') -> Dict[str, any]:
        """
        Genera un reporte consolidado en formato PDF
        
        Args:
            detections_by_file: Diccionario con detecciones por archivo
            audio_files: Lista de archivos de audio procesados
            output_dir: Directorio donde guardar el reporte
            
        Returns:
            Diccionario con información del reporte generado
        """
        # Crear nombre del archivo PDF
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_name = f'Reporte_Consolidado_{timestamp}.pdf'
        report_path = os.path.join(output_dir, report_name)
        
        # Configurar el documento PDF
        doc = SimpleDocTemplate(report_path, pagesize=letter,
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Contenedor de elementos del PDF
        story = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a5490'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1a5490'),
            spaceAfter=12,
            spaceBefore=12
        )
        normal_style = styles['Normal']
        
        # Título
        title = Paragraph("Reporte Consolidado de Análisis de Audio", title_style)
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Información General
        story.append(Paragraph("Información General", heading_style))
        fecha_analisis = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        story.append(Paragraph(f"<b>Fecha de análisis:</b> {fecha_analisis}", normal_style))
        story.append(Paragraph(f"<b>Número de archivos analizados:</b> {len(audio_files)}", normal_style))
        story.append(Spacer(1, 20))
        
        # Lista de archivos procesados
        story.append(Paragraph("Archivos Procesados", heading_style))
        for i, audio_file in enumerate(audio_files, 1):
            file_name = os.path.basename(audio_file) if isinstance(audio_file, str) else audio_file
            story.append(Paragraph(f"{i}. {file_name}", normal_style))
        story.append(Spacer(1, 20))
        
        # Crear y agregar gráfico resumen
        chart_path = os.path.join(output_dir, 'temp_summary_chart.png')
        ReportService.create_summary_chart(detections_by_file, chart_path)
        
        story.append(Paragraph("Gráfico Resumen de Detecciones", heading_style))
        story.append(Paragraph("El siguiente gráfico muestra un resumen de las detecciones encontradas en cada archivo de audio:", normal_style))
        story.append(Spacer(1, 12))
        
        try:
            # Agregar imagen del gráfico
            img = RLImage(chart_path, width=6.5*inch, height=4*inch)
            story.append(img)
            story.append(Spacer(1, 20))
        except Exception as e:
            story.append(Paragraph(f"Error al insertar gráfico: {e}", normal_style))
            story.append(Spacer(1, 12))
        
        # Resumen Estadístico
        story.append(Paragraph("Resumen Estadístico", heading_style))
        
        total_segments = 0
        total_detections = 0
        estadisticas = []
        
        for file_prefix, data in detections_by_file.items():
            segments_count = len(data['segments'])
            detections_count = len(data['detections'])
            total_segments += segments_count
            total_detections += detections_count
            
            detection_percentage = (detections_count / segments_count * 100) if segments_count > 0 else 0
            estadisticas.append(f"• <b>{file_prefix}:</b> {detections_count}/{segments_count} segmentos con detección ({detection_percentage:.1f}%)")
        
        for stat in estadisticas:
            story.append(Paragraph(stat, normal_style))
        
        story.append(Spacer(1, 12))
        overall_percentage = (total_detections / total_segments * 100) if total_segments > 0 else 0
        resumen_general = f"<b>Resumen general:</b> {total_detections}/{total_segments} segmentos con detección ({overall_percentage:.1f}%)"
        story.append(Paragraph(resumen_general, normal_style))
        
        # ── Sección: Espectrogramas analizados ──────────────────────────────────
        story.append(PageBreak())

        detection_label_style = ParagraphStyle(
            'DetectionSegment',
            parent=normal_style,
            textColor=colors.red,
            fontName='Helvetica-Bold',
            fontSize=11,
            spaceAfter=4
        )
        normal_segment_style = ParagraphStyle(
            'NormalSegment',
            parent=normal_style,
            fontSize=11,
            spaceAfter=4
        )

        story.append(Paragraph("Espectrogramas Analizados", heading_style))
        story.append(Paragraph(
            "Se muestran todos los espectrogramas generados durante el análisis. "
            "Los segmentos marcados en rojo contienen una posible detección de corte.",
            normal_style
        ))
        story.append(Spacer(1, 12))

        for file_prefix, data in detections_by_file.items():
            story.append(Paragraph(f"<b>Archivo:</b> {file_prefix}", normal_style))
            story.append(Spacer(1, 6))

            segments_sorted = sorted(data['segments'], key=lambda seg: seg['start'])

            for segment in segments_sorted:
                start_str = ReportService._seconds_to_mmss(segment['start'])
                end_str = ReportService._seconds_to_mmss(segment['end'])
                time_range = f"{start_str} - {end_str}"

                if segment.get('has_detection'):
                    seg_label = Paragraph(
                        f"<b>&#9888; Posible detecci&#243;n &mdash; {time_range}</b>",
                        detection_label_style
                    )
                else:
                    seg_label = Paragraph(
                        f"Segmento: {time_range}",
                        normal_segment_style
                    )

                story.append(seg_label)

                img_path = segment.get('image_path')
                if img_path and os.path.exists(img_path):
                    try:
                        spec_img = RLImage(img_path, width=6 * inch, height=2.5 * inch)
                        story.append(spec_img)
                    except Exception as img_err:
                        story.append(Paragraph(f"(Error al insertar imagen: {img_err})", normal_style))
                else:
                    story.append(Paragraph("(Imagen no disponible)", normal_style))

                story.append(Spacer(1, 8))

            story.append(Spacer(1, 16))

        # Generar el PDF
        doc.build(story)
        
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
