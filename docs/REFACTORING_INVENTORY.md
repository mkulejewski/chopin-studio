# Source inventory at 6c07577446615e254a478ccadd6ee2653a5043b2

Static inventory of every production Python/TypeScript/CSS file; imports include deferred imports. Runtime tests remain authoritative.

| Module | Lines | Largest callable | Internal dependencies |
| --- | ---: | --- | --- |
| `backend/chopin/__init__.py` | 1 | — |  |
| `backend/chopin/__main__.py` | 38 | `request_shutdown` (4) | app, desktop, store |
| `backend/chopin/app.py` | 511 | `create_app` (428) | catalogue, headphone_audio, jobs, learning_api, live, microphone, midi_files, practice_api, recorder, retention, store |
| `backend/chopin/assessment.py` | 49 | `piece_assessment` (22) | midi_files |
| `backend/chopin/catalogue.py` | 81 | `seed_repertoire` (22) |  |
| `backend/chopin/desktop.py` | 25 | `close_studio_windows` (16) |  |
| `backend/chopin/extraction.py` | 48 | `segment_midi` (42) | midi_files, velocity |
| `backend/chopin/hardware_audio.py` | 52 | `play` (42) | extraction |
| `backend/chopin/headphone_audio.py` | 148 | `assess_piano_presence` (107) | microphone |
| `backend/chopin/jobs.py` | 135 | `render` (50) | extraction, headphone_audio, organisation, retention |
| `backend/chopin/learning.py` | 830 | `evaluate` (71) | learning_staves, midi_files |
| `backend/chopin/learning_api.py` | 256 | `attach_learning_routes` (177) | learning, learning_score |
| `backend/chopin/learning_score.py` | 104 | `attack_score_xml` (94) |  |
| `backend/chopin/learning_staves.py` | 153 | `comparison` (45) | learning |
| `backend/chopin/lifecycle.py` | 24 | `expired` (8) |  |
| `backend/chopin/live.py` | 212 | `tick` (107) | organisation, tempo |
| `backend/chopin/microphone.py` | 353 | `analyse_audio` (72) | headphone_audio |
| `backend/chopin/microphone_capture.py` | 46 | `main` (31) |  |
| `backend/chopin/midi_files.py` | 144 | `export_midi` (41) |  |
| `backend/chopin/musical_comparison.py` | 133 | `musical_review` (69) |  |
| `backend/chopin/organisation.py` | 466 | `organise` (110) | assessment, microphone, midi_files, musical_comparison, passages, retention, symbolic, tempo, velocity |
| `backend/chopin/passages.py` | 123 | `passage_analysis` (89) |  |
| `backend/chopin/practice_api.py` | 662 | `attach_practice_routes` (560) | assessment, extraction, hardware_audio, microphone, midi_files, organisation, passages, progress, retention, symbolic, teacher |
| `backend/chopin/progress.py` | 112 | `piece_progress` (72) |  |
| `backend/chopin/recorder.py` | 397 | `start` (54) | microphone, midi_files, retention |
| `backend/chopin/retention.py` | 403 | `catalogue` (70) | microphone, organisation |
| `backend/chopin/store.py` | 73 | `__init__` (26) | catalogue |
| `backend/chopin/symbolic.py` | 181 | `annotate_reference_staves` (62) |  |
| `backend/chopin/teacher.py` | 72 | `local_report` (28) | assessment |
| `backend/chopin/tempo.py` | 90 | `infer_tempo` (62) | organisation |
| `backend/chopin/velocity.py` | 46 | `velocity_events` (40) |  |

## Frontend import graph

| Module | Lines | Local imports |
| --- | ---: | --- |
| `frontend/src/AiConfig.tsx` | 49 | ./api, ./TouchButton |
| `frontend/src/AnalysisEvidence.tsx` | 763 | ./PassageComparison, ./captureWarning, ./comparisonJudgement, ./ScoreComparison, ./comparisonScore, ./api, ./TouchButton |
| `frontend/src/CompareTakes.tsx` | 192 | ./PassageComparison, ./ScoreComparison, ./api, ./TouchButton |
| `frontend/src/Learning.tsx` | 1567 | ./ReasonDictation, ./LearningStaves, ./api, ./Score, ./TouchButton |
| `frontend/src/LearningStaves.tsx` | 276 | ./AnalysisEvidence, ./api, ./comparisonScore, ./TouchButton |
| `frontend/src/LivePanel.tsx` | 252 | ./api, ./TouchButton |
| `frontend/src/PassageComparison.tsx` | 508 | ./api, ./TouchButton |
| `frontend/src/PieceSessions.tsx` | 95 | ./activityTypes, ./api, ./TouchButton |
| `frontend/src/PracticeProgress.tsx` | 408 | ./api, ./TouchButton |
| `frontend/src/PracticeReview.tsx` | 1011 | ./AnalysisEvidence, ./activityTypes, ./AiConfig, ./api, ./TouchButton |
| `frontend/src/ProgressHistory.tsx` | 164 | ./PracticeProgress, ./TouchButton, ./api |
| `frontend/src/ReasonDictation.tsx` | 72 | ./TouchButton, ./reasonDictation, ./speechRecognition |
| `frontend/src/RecordingCleanup.tsx` | 385 | ./api, ./TouchButton |
| `frontend/src/RecordingsLibrary.tsx` | 354 | ./captureWarning, ./api, ./activityTypes, ./TouchButton |
| `frontend/src/References.tsx` | 366 | ./SymbolicPreview, ./api, ./TouchButton |
| `frontend/src/Score.tsx` | 776 | ./SymbolicPreview, ./TouchButton, ./pdfRenderer, ./pdfCache, ./api |
| `frontend/src/ScoreComparison.tsx` | 293 | ./comparisonJudgement, ./AnalysisEvidence, ./comparisonScore, ./TouchButton |
| `frontend/src/SessionsList.tsx` | 124 | ./captureWarning, ./api, ./RecordingCleanup, ./sessionGroups, ./TouchButton |
| `frontend/src/SymbolicPreview.tsx` | 86 | ./api, ./TouchButton |
| `frontend/src/TouchButton.tsx` | 77 |  |
| `frontend/src/VoiceControl.tsx` | 165 | ./TouchButton, ./speechRecognition |
| `frontend/src/activityTypes.ts` | 8 |  |
| `frontend/src/api.test.ts` | 27 | ./api |
| `frontend/src/api.ts` | 95 |  |
| `frontend/src/captureWarning.test.ts` | 32 | ./captureWarning |
| `frontend/src/captureWarning.ts` | 26 |  |
| `frontend/src/comparisonJudgement.ts` | 23 | ./AnalysisEvidence |
| `frontend/src/comparisonPdf.ts` | 153 | ./AnalysisEvidence, ./comparisonJudgement, ./comparisonScore |
| `frontend/src/comparisonScore.test.ts` | 327 | ./comparisonScore, ./AnalysisEvidence |
| `frontend/src/comparisonScore.ts` | 506 | ./comparisonJudgement, ./AnalysisEvidence |
| `frontend/src/main.tsx` | 2194 | ./CompareTakes, ./captureWarning, ./RecordingsLibrary, ./SessionsList, ./Learning, ./RecordingCleanup, ./PracticeReview, ./PieceSessions, ./References, ./LivePanel, ./ProgressHistory, ./TouchButton, ./VoiceControl, ./voiceCommands, ./api, ./Score, ./pdfCache, ./style.css |
| `frontend/src/pdfCache.test.ts` | 48 |  |
| `frontend/src/pdfCache.ts` | 50 |  |
| `frontend/src/pdfRenderer.test.ts` | 145 | ./pdfRenderer |
| `frontend/src/pdfRenderer.ts` | 165 |  |
| `frontend/src/reasonDictation.test.ts` | 88 | ./reasonDictation, ./speechRecognition |
| `frontend/src/reasonDictation.ts` | 106 | ./speechRecognition |
| `frontend/src/sessionGroups.test.ts` | 84 | ./sessionGroups, ./api |
| `frontend/src/sessionGroups.ts` | 89 | ./api |
| `frontend/src/speechRecognition.ts` | 22 |  |
| `frontend/src/style.css` | 2972 |  |
| `frontend/src/vite-env.d.ts` | 1 |  |
| `frontend/src/voiceCommands.test.ts` | 67 | ./voiceCommands, ./api |
| `frontend/src/voiceCommands.ts` | 109 | ./api |

## Baseline HTTP endpoints

- `GET /api/learning` → `learning_api.py:catalogue`
- `POST /api/learning/selection` → `learning_api.py:select_piece`
- `GET /api/learning/{piece}` → `learning_api.py:get`
- `GET /api/learning/{piece}/reference` → `learning_api.py:reference`
- `PUT /api/learning/{piece}` → `learning_api.py:configure`
- `PUT /api/learning/{piece}/hand` → `learning_api.py:select_hand`
- `POST /api/learning/{piece}/pedal-control` → `learning_api.py:pedal_control`
- `GET /api/learning/{piece}/pedal-commands` → `learning_api.py:pedal_commands`
- `POST /api/learning/{piece}/pedal-repeat` → `learning_api.py:pedal_repeat`
- `POST /api/learning/{piece}/start` → `learning_api.py:start`
- `POST /api/learning/{piece}/finish` → `learning_api.py:finish`
- `POST /api/learning/{piece}/peek` → `learning_api.py:peek`
- `POST /api/learning/{piece}/pause` → `learning_api.py:pause`
- `POST /api/learning/{piece}/restart` → `learning_api.py:restart`
- `POST /api/learning/{piece}/variants` → `learning_api.py:variant`
- `POST /api/learning/{piece}/corrections` → `learning_api.py:correct_reference`
- `POST /api/learning/{piece}/attempts/{ident}/accept` → `learning_api.py:accept_take`
- `POST /api/learning/{piece}/advance` → `learning_api.py:advance_stage`
- `POST /api/learning/{piece}/restart-take` → `learning_api.py:restart_take`
- `POST /api/learning/{piece}/review` → `learning_api.py:review`
- `POST /api/learning/{piece}/review/leave` → `learning_api.py:leave_review`
- `GET /api/learning/{piece}/attempts/{ident}/staves` → `learning_api.py:live_staves`
- `GET /api/status` → `app.py:status`
- `POST /api/shutdown` → `app.py:shutdown_service`
- `POST /api/record/start` → `app.py:start`
- `POST /api/record/stop` → `app.py:stop`
- `GET /api/sessions` → `app.py:sessions`
- `GET /api/sessions/{ident}/microphone` → `app.py:microphone_download`
- `GET /api/sessions/{ident}/recording` → `app.py:recording_info`
- `GET /api/sessions/{ident}/midi` → `app.py:download`
- `GET /api/sessions/{ident}/summary` → `app.py:summary`
- `POST /api/import/midi` → `app.py:import_midi`
- `GET /api/library` → `app.py:library`
- `PUT /api/pieces/{ident}` → `app.py:update_piece`
- `PUT /api/pieces/{ident}/view` → `app.py:update_view`
- `POST /api/volumes/{ident}/pdf` → `app.py:import_pdf`
- `GET /api/volumes/{ident}/pdf` → `app.py:pdf`
- `GET /api/settings` → `app.py:get_settings`
- `PUT /api/settings` → `app.py:save_settings`
- `POST /api/devices/reconnect` → `app.py:reconnect`
- `GET /api/page-commands` → `app.py:page_commands`
- `POST /api/simulation/start` → `app.py:simulate`
- `POST /api/simulation/stop` → `app.py:stop_simulation`
- `GET /api/recordings` → `practice_api.py:recordings`
- `GET /api/recordings/library` → `practice_api.py:recordings_library`
- `PUT /api/recordings/{ident}` → `practice_api.py:recording_choice`
- `DELETE /api/recordings/{ident}` → `practice_api.py:remove_take`
- `DELETE /api/recordings/{ident}/audio` → `practice_api.py:remove_take`
- `DELETE /api/sessions/{ident}` → `practice_api.py:remove_session`
- `GET /api/ai/config` → `practice_api.py:ai_config`
- `PUT /api/ai/config` → `practice_api.py:ai_key`
- `POST /api/reports/{ident}/revision` → `practice_api.py:revise_report`
- `GET /api/pieces/{ident}/references` → `practice_api.py:references`
- `GET /api/pieces/{ident}/sessions` → `practice_api.py:piece_sessions`
- `POST /api/pieces/{ident}/references` → `practice_api.py:reference_import`
- `GET /api/references/{ident}` → `practice_api.py:reference`
- `GET /api/references/{ident}/musicxml` → `practice_api.py:reference_download`
- `PUT /api/references/{ident}` → `practice_api.py:edit_reference`
- `GET /api/pieces/{ident}/pages` → `practice_api.py:pages`
- `PUT /api/pieces/{ident}/pages` → `practice_api.py:page_map`
- `GET /api/sessions/{ident}/segments` → `practice_api.py:timeline`
- `POST /api/sessions/{ident}/organise` → `practice_api.py:organise`
- `PUT /api/sessions/{ident}/segments` → `practice_api.py:edit_timeline`
- `POST /api/sessions/{ident}/segments/undo` → `practice_api.py:undo`
- `GET /api/segments/{ident}/audio-status` → `practice_api.py:segment_audio_status`
- `GET /api/segments/{ident}/microphone` → `practice_api.py:microphone_segment`
- `GET /api/segments/{ident}/midi` → `practice_api.py:export_segment`
- `POST /api/segments/{ident}/learn` → `practice_api.py:learn`
- `POST /api/segments/{ident}/analyse` → `practice_api.py:analyse`
- `GET /api/sessions/{ident}/analyses` → `practice_api.py:analyses`
- `GET /api/jobs` → `practice_api.py:job_list`
- `POST /api/jobs/{ident}/cancel` → `practice_api.py:cancel`
- `GET /api/pieces/{ident}/assessment` → `practice_api.py:assessment`
- `GET /api/sessions/{ident}/preanalysis` → `practice_api.py:preanalysis`
- `GET /api/audio/hardware` → `practice_api.py:hardware`
- `POST /api/segments/{ident}/ap470` → `practice_api.py:ap470`
- `POST /api/segments/{ident}/audio` → `practice_api.py:import_audio`
- `GET /api/audio/engines` → `practice_api.py:engines`
- `POST /api/segments/{ident}/render` → `practice_api.py:render`
- `GET /api/audio/{ident}` → `practice_api.py:audio`
- `DELETE /api/audio/{ident}` → `practice_api.py:delete_audio`
- `GET /api/performances` → `practice_api.py:performances`
- `GET /api/comparison` → `practice_api.py:comparison`
- `GET /api/progress/days` → `practice_api.py:days`
- `GET /api/sessions/{ident}/bundle` → `practice_api.py:bundle`
- `PUT /api/live/context` → `practice_api.py:live_context`
- `GET /api/live` → `practice_api.py:live_status`
- `GET /api/progress` → `practice_api.py:progress`
- `GET /api/pieces/{piece_id}/voicing` → `practice_api.py:voicing`
- `PUT /api/pieces/{piece_id}/voicing` → `practice_api.py:save_voicing`
- `POST /api/pieces/{piece_id}/objectives` → `practice_api.py:add_objective`
- `PUT /api/objectives/{ident}` → `practice_api.py:edit_objective`
- `POST /api/objectives/{ident}/time` → `practice_api.py:attribute_time`
- `DELETE /api/objectives/{ident}/time/{time_id}` → `practice_api.py:remove_time`
- `POST /api/sessions/{ident}/teacher` → `practice_api.py:teacher`
- `GET /api/sessions/{ident}/reports` → `practice_api.py:reports`
- `GET /api/reports/{ident}/text` → `practice_api.py:report_text`
