for name in "upload" "exec" "ocr"; do modal deploy helper_"$name".py; done
for name in "EnglishDiffBot" "LinkAwareBot" "nougatOCR" "RunPythonCode" "PythonAgent" "matplotlib" "TesseractOCR" "tiktoken" "ResumeReview" "PromotedAnswer" "MeguminWizardEx"; do modal deploy --name "$name" bot_"$name".py ; curl -X POST https://api.poe.com/bot/fetch_settings/"$name"/$POE_API_KEY ; done
