from google.cloud import videointelligence
from google.cloud import storage
from moviepy.editor import VideoFileClip
import os
from typing import Dict, List, Optional
import json
from ..config import get_settings

settings = get_settings()

class VideoAnalysisService:
    def __init__(self):
        self.video_client = videointelligence.VideoIntelligenceServiceClient()
        self.storage_client = storage.Client()
        self.bucket_name = settings.GCP_BUCKET_NAME

    async def upload_to_gcs(self, file_path: str) -> str:
        """Upload video to Google Cloud Storage for analysis"""
        bucket = self.storage_client.bucket(self.bucket_name)
        blob_name = os.path.basename(file_path)
        blob = bucket.blob(f"temp_analysis/{blob_name}")
        
        blob.upload_from_filename(file_path)
        return f"gs://{self.bucket_name}/temp_analysis/{blob_name}"

    async def get_local_metadata(self, file_path: str) -> Dict:
        """Get basic video metadata using moviepy"""
        clip = VideoFileClip(file_path)
        size = os.path.getsize(file_path)
        
        return {
            "duration": clip.duration,
            "size_mb": size / (1024 * 1024),
            "resolution": f"{clip.size[0]}x{clip.size[1]}",
            "fps": clip.fps,
            "has_audio": clip.audio is not None
        }

    async def analyze_video(self, file_path: str) -> Dict:
        """Comprehensive video analysis using Google Cloud Video Intelligence"""
        # Get local metadata first
        metadata = await self.get_local_metadata(file_path)
        
        # Upload to GCS for analysis
        gcs_uri = await self.upload_to_gcs(file_path)
        
        # Configure the analysis request
        features = [
            videointelligence.Feature.LABEL_DETECTION,
            videointelligence.Feature.SHOT_CHANGE_DETECTION,
            videointelligence.Feature.SPEECH_TRANSCRIPTION,
            videointelligence.Feature.TEXT_DETECTION,
            videointelligence.Feature.EXPLICIT_CONTENT_DETECTION
        ]
        
        video_context = videointelligence.VideoContext(
            speech_transcription_config=videointelligence.SpeechTranscriptionConfig(
                language_code="en-US",
                enable_automatic_punctuation=True,
            )
        )
        
        # Start the analysis
        operation = self.video_client.annotate_video(
            request={
                "features": features,
                "input_uri": gcs_uri,
                "video_context": video_context,
            }
        )
        
        print("Processing video...")
        result = operation.result(timeout=300)
        
        # Process results
        analysis_results = {
            "metadata": metadata,
            "labels": self._process_labels(result.annotation_results[0].shot_label_annotations),
            "shots": self._process_shots(result.annotation_results[0].shot_annotations),
            "texts": self._process_text(result.annotation_results[0].text_annotations),
            "explicit_content": self._process_explicit_content(result.annotation_results[0].explicit_annotation),
            "transcription": self._process_transcription(result.annotation_results[0].speech_transcriptions)
        }
        
        # Clean up GCS
        bucket = self.storage_client.bucket(self.bucket_name)
        blob = bucket.blob(f"temp_analysis/{os.path.basename(file_path)}")
        blob.delete()
        
        return analysis_results

    def _process_labels(self, labels) -> List[Dict]:
        """Process and format label annotations"""
        processed_labels = []
        for label in labels:
            label_info = {
                "description": label.entity.description,
                "confidence": label.frames[0].confidence,
                "segments": [{
                    "start_time": segment.start_time_offset.total_seconds(),
                    "end_time": segment.end_time_offset.total_seconds()
                } for segment in label.segments]
            }
            processed_labels.append(label_info)
        return processed_labels

    def _process_shots(self, shots) -> List[Dict]:
        """Process and format shot change annotations"""
        return [{
            "start_time": shot.start_time_offset.total_seconds(),
            "end_time": shot.end_time_offset.total_seconds()
        } for shot in shots]

    def _process_text(self, texts) -> List[Dict]:
        """Process and format text annotations"""
        return [{
            "text": text.text,
            "confidence": text.segments[0].confidence,
            "start_time": text.segments[0].start_time_offset.total_seconds(),
            "end_time": text.segments[0].end_time_offset.total_seconds()
        } for text in texts]

    def _process_explicit_content(self, explicit_annotation) -> List[Dict]:
        """Process and format explicit content annotations"""
        return [{
            "time": frame.time_offset.total_seconds(),
            "likelihood": videointelligence.Likelihood(frame.pornography_likelihood).name
        } for frame in explicit_annotation.frames]

    def _process_transcription(self, transcriptions) -> List[Dict]:
        """Process and format speech transcriptions"""
        processed_transcriptions = []
        for transcription in transcriptions:
            for alternative in transcription.alternatives:
                processed_transcriptions.append({
                    "transcript": alternative.transcript,
                    "confidence": alternative.confidence,
                    "words": [{
                        "word": word.word,
                        "start_time": word.start_time.total_seconds(),
                        "end_time": word.end_time.total_seconds(),
                        "confidence": word.confidence
                    } for word in alternative.words]
                })
        return processed_transcriptions
