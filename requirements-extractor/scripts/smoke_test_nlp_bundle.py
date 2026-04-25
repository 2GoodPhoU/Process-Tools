#!/usr/bin/env python3
"""Quick smoke test for NLP bundle readiness.

This script verifies that:
1. spaCy and the model are installed (or will be included in the bundle)
2. Basic NLP-dependent functions work
3. No outbound network calls are triggered during actor extraction

Note: This is a pre-build check, not a PyInstaller validation.
Run this on the target environment AFTER building the executable.
"""

import sys
import pathlib

def test_nlp_loadable():
    """Test that spaCy and model can be imported."""
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        print("✓ spaCy and en_core_web_sm are available")
        return True
    except ImportError as e:
        print(f"✗ NLP not available: {e}")
        return False

def test_nlp_actor_extraction():
    """Test that NLP-based actor extraction works."""
    try:
        from requirements_extractor.actors import ActorResolver
        
        resolver = ActorResolver(use_nlp=True)
        if resolver.nlp is None:
            print("✗ ActorResolver initialized with use_nlp=True but NLP is None")
            return False
        
        # Simple test sentence
        doc = resolver.nlp("John and Mary reviewed the specification.")
        persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
        
        if persons:
            print(f"✓ NLP-based NER works: {persons}")
            return True
        else:
            print("⚠ NER produced no entities (model may not be configured correctly)")
            return False
    except Exception as e:
        print(f"✗ Actor extraction test failed: {e}")
        return False

def test_no_outbound_calls():
    """Monkey-patch requests/urllib/httpx to catch outbound calls."""
    import sys
    from unittest.mock import patch
    
    blocked_modules = []
    
    def block_request(*args, **kwargs):
        raise RuntimeError(f"Outbound network call detected: {args}")
    
    with patch("urllib.request.urlopen", side_effect=block_request):
        with patch("requests.get", side_effect=block_request):
            with patch("requests.post", side_effect=block_request):
                try:
                    from requirements_extractor.actors import ActorResolver
                    resolver = ActorResolver(use_nlp=True)
                    
                    if resolver.nlp is not None:
                        print("✓ NLP initialization made no outbound calls")
                        return True
                    else:
                        print("⚠ NLP was not loaded")
                        return False
                except RuntimeError as e:
                    if "Outbound network call detected" in str(e):
                        print(f"✗ Outbound call attempted: {e}")
                        return False
                    raise
                except Exception as e:
                    print(f"✗ Test failed: {e}")
                    return False

def main():
    print("=== NLP Bundle Smoke Test ===\n")
    
    results = {
        "NLP loadable": test_nlp_loadable(),
        "Actor extraction": test_nlp_actor_extraction(),
        "No outbound calls": test_no_outbound_calls(),
    }
    
    print("\n=== Summary ===")
    for test, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"{test}: {status}")
    
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
