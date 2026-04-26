#!/usr/bin/env python3
"""Run batch tests on 25 PDFs and collect metrics for analysis."""

import asyncio
import json
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

import aiohttp
import aiofiles

# Configuration
API_BASE = "http://localhost:8000"
PDF_DIR = Path(__file__).resolve().parent / "pdfs"
OUTPUT_FILE = Path(__file__).resolve().parent / "test_results.json"


class BatchTester:
    """Test runner for batch PDF processing."""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.session: aiohttp.ClientSession = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def check_health(self) -> bool:
        """Check if backend is running."""
        try:
            async with self.session.get(f"{API_BASE}/health") as resp:
                return resp.status == 200
        except Exception as e:
            print(f"❌ Backend not available: {e}")
            return False
    
    async def upload_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Upload a single PDF and return metrics."""
        start_time = time.time()
        result = {
            "filename": pdf_path.name,
            "file_size_bytes": pdf_path.stat().st_size,
            "upload_start": datetime.now().isoformat(),
            "success": False,
            "error": None,
        }
        
        try:
            # Read and upload file
            async with aiofiles.open(pdf_path, "rb") as f:
                content = await f.read()
            
            data = aiohttp.FormData()
            data.add_field("file", content, filename=pdf_path.name, content_type="application/pdf")
            
            async with self.session.post(f"{API_BASE}/upload", data=data) as resp:
                result["http_status"] = resp.status
                result["response_time_sec"] = time.time() - start_time
                
                if resp.status == 200:
                    data = await resp.json()
                    result["document_id"] = data.get("document_id")
                    result["status"] = data.get("status")
                    result["message"] = data.get("message")
                    result["success"] = True
                    
                    # Extract metrics from message
                    msg = data.get("message", "")
                    if "pages extracted" in msg:
                        try:
                            pages = int(msg.split("pages extracted")[0].split()[-1])
                            result["pages_extracted"] = pages
                        except:
                            pass
                    if "chunks indexed" in msg:
                        try:
                            chunks = int(msg.split("chunks indexed")[0].split()[-1])
                            result["chunks_indexed"] = chunks
                        except:
                            pass
                else:
                    result["error"] = await resp.text()
                    result["success"] = False
                    
        except Exception as e:
            result["error"] = str(e)
            result["response_time_sec"] = time.time() - start_time
            result["success"] = False
        
        result["upload_end"] = datetime.now().isoformat()
        return result
    
    async def get_document_details(self, document_id: str) -> Dict[str, Any]:
        """Get document details after processing."""
        try:
            async with self.session.get(f"{API_BASE}/documents/{document_id}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "doc_type": data.get("doc_type"),
                        "language": data.get("language"),
                        "status": data.get("status"),
                        "metadata": data.get("metadata", {}),
                    }
        except Exception as e:
            return {"error": str(e)}
        return {}
    
    async def run_tests(self) -> Dict[str, Any]:
        """Run all tests and collect metrics."""
        print("=" * 70)
        print("DOCUMIND AI BATCH TEST RUNNER")
        print("=" * 70)
        
        # Check backend health
        print("\n1. Checking backend health...")
        if not await self.check_health():
            print("❌ Backend is not running. Please start it first:")
            print("   cd backend && uvicorn api.main:app --reload")
            return {"error": "Backend not available"}
        print("✅ Backend is healthy")
        
        # Find all PDFs
        print("\n2. Scanning for PDFs...")
        if not PDF_DIR.exists():
            print(f"❌ PDF directory not found: {PDF_DIR}")
            print("   Run generate_test_pdfs.py first")
            return {"error": "No PDFs found"}
        
        pdf_files = sorted([f for f in PDF_DIR.iterdir() if f.suffix.lower() == ".pdf"])
        print(f"✅ Found {len(pdf_files)} PDFs")
        
        # Run upload tests
        print("\n3. Running upload tests...")
        print("-" * 70)
        
        overall_start = time.time()
        
        for i, pdf in enumerate(pdf_files, 1):
            print(f"[{i}/{len(pdf_files)}] Uploading {pdf.name}...", end=" ", flush=True)
            
            result = await self.upload_pdf(pdf)
            
            if result["success"]:
                print(f"✅ {result['response_time_sec']:.2f}s | "
                      f"{result.get('pages_extracted', '?')} pages | "
                      f"{result.get('chunks_indexed', '?')} chunks")
                
                # Get additional details if upload succeeded
                if result.get("document_id"):
                    details = await self.get_document_details(result["document_id"])
                    result.update(details)
            else:
                print(f"❌ Error: {result.get('error', 'Unknown')[:50]}")
            
            self.results.append(result)
            
            # Small delay between uploads to not overwhelm the system
            await asyncio.sleep(0.5)
        
        overall_end = time.time()
        
        # Calculate summary statistics
        print("\n4. Calculating statistics...")
        summary = self._calculate_summary(overall_end - overall_start)
        
        # Save results
        print("\n5. Saving results...")
        output_data = {
            "test_run": {
                "timestamp": datetime.now().isoformat(),
                "total_pdfs": len(pdf_files),
                "api_base": API_BASE,
            },
            "summary": summary,
            "results": self.results,
        }
        
        with open(OUTPUT_FILE, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"✅ Results saved to {OUTPUT_FILE}")
        
        # Print summary
        self._print_summary(summary)
        
        return output_data
    
    def _calculate_summary(self, total_time: float) -> Dict[str, Any]:
        """Calculate summary statistics."""
        successful = [r for r in self.results if r["success"]]
        failed = [r for r in self.results if not r["success"]]
        
        response_times = [r["response_time_sec"] for r in successful]
        file_sizes = [r["file_size_bytes"] for r in successful]
        pages = [r.get("pages_extracted", 0) for r in successful if r.get("pages_extracted")]
        chunks = [r.get("chunks_indexed", 0) for r in successful if r.get("chunks_indexed")]
        
        doc_types = {}
        for r in successful:
            doc_type = r.get("doc_type", "unknown")
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
        
        return {
            "total_tests": len(self.results),
            "successful_uploads": len(successful),
            "failed_uploads": len(failed),
            "success_rate_pct": round(len(successful) / len(self.results) * 100, 1) if self.results else 0,
            "total_time_sec": round(total_time, 2),
            "avg_response_time_sec": round(sum(response_times) / len(response_times), 2) if response_times else 0,
            "min_response_time_sec": round(min(response_times), 2) if response_times else 0,
            "max_response_time_sec": round(max(response_times), 2) if response_times else 0,
            "total_data_uploaded_mb": round(sum(file_sizes) / (1024 * 1024), 2),
            "avg_file_size_kb": round(sum(file_sizes) / len(file_sizes) / 1024, 2) if file_sizes else 0,
            "total_pages_processed": sum(pages),
            "total_chunks_indexed": sum(chunks),
            "avg_pages_per_doc": round(sum(pages) / len(pages), 1) if pages else 0,
            "avg_chunks_per_doc": round(sum(chunks) / len(chunks), 1) if chunks else 0,
            "document_types": doc_types,
            "failures": [
                {
                    "filename": r["filename"],
                    "error": r.get("error", "Unknown")[:100],
                }
                for r in failed
            ],
        }
    
    def _print_summary(self, summary: Dict[str, Any]):
        """Print a formatted summary."""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total PDFs tested:       {summary['total_tests']}")
        print(f"Successful uploads:      {summary['successful_uploads']}")
        print(f"Failed uploads:          {summary['failed_uploads']}")
        print(f"Success rate:            {summary['success_rate_pct']}%")
        print(f"\nTotal time:              {summary['total_time_sec']:.2f} seconds")
        print(f"Avg response time:       {summary['avg_response_time_sec']:.2f} seconds")
        print(f"Min response time:       {summary['min_response_time_sec']:.2f} seconds")
        print(f"Max response time:       {summary['max_response_time_sec']:.2f} seconds")
        print(f"\nTotal data uploaded:     {summary['total_data_uploaded_mb']:.2f} MB")
        print(f"Avg file size:           {summary['avg_file_size_kb']:.2f} KB")
        print(f"\nTotal pages processed:   {summary['total_pages_processed']}")
        print(f"Total chunks indexed:    {summary['total_chunks_indexed']}")
        print(f"Avg pages per doc:       {summary['avg_pages_per_doc']}")
        print(f"Avg chunks per doc:      {summary['avg_chunks_per_doc']}")
        print(f"\nDocument types detected:")
        for doc_type, count in summary['document_types'].items():
            print(f"  - {doc_type}: {count}")
        
        if summary['failures']:
            print(f"\n❌ Failures ({len(summary['failures'])}):")
            for f in summary['failures']:
                print(f"  - {f['filename']}: {f['error']}")
        
        print("=" * 70)


async def main():
    """Main entry point."""
    async with BatchTester() as tester:
        results = await tester.run_tests()
    return results


if __name__ == "__main__":
    # Check if aiohttp is available
    try:
        import aiohttp
        import aiofiles
    except ImportError:
        print("Installing required packages...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "aiohttp", "aiofiles", "-q"])
        print("✅ Packages installed, please run again")
        sys.exit(0)
    
    asyncio.run(main())
