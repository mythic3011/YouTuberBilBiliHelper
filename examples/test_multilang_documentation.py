#!/usr/bin/env python3
"""
Multi-Language Documentation Test Suite

Tests the multi-language README setup, language navigation,
and content consistency across different language versions.
"""

import sys
import os
from pathlib import Path
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiLanguageDocumentationTester:
    """Test suite for multi-language documentation."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.test_results = []
        
        # Expected language files
        self.expected_languages = {
            "README.md": {"lang": "English", "flag": "🇺🇸", "code": "en"},
            "README.zh-CN.md": {"lang": "简体中文", "flag": "🇨🇳", "code": "zh-CN"},
            "README.zh-HK.md": {"lang": "繁體中文 (香港)", "flag": "🇭🇰", "code": "zh-HK"},
            "README.ja.md": {"lang": "日本語", "flag": "🇯🇵", "code": "ja"},
            "README.ko.md": {"lang": "한국어", "flag": "🇰🇷", "code": "ko"},
            "README.es.md": {"lang": "Español", "flag": "🇪🇸", "code": "es"},
            "README.fr.md": {"lang": "Français", "flag": "🇫🇷", "code": "fr"}
        }
    
    def test_file_existence(self) -> bool:
        """Test that all expected language files exist."""
        logger.info("🔍 Testing Language File Existence")
        
        existing_files = []
        missing_files = []
        
        for filename, info in self.expected_languages.items():
            file_path = self.project_root / filename
            if file_path.exists():
                existing_files.append(filename)
                logger.info(f"✅ Found: {filename} ({info['lang']})")
            else:
                missing_files.append(filename)
                logger.error(f"❌ Missing: {filename} ({info['lang']})")
        
        result = {
            "test": "Language File Existence",
            "total_expected": len(self.expected_languages),
            "existing_files": len(existing_files),
            "missing_files": len(missing_files),
            "success": len(missing_files) == 0,
            "existing": existing_files,
            "missing": missing_files
        }
        
        self.test_results.append(result)
        return result["success"]
    
    def test_language_navigation_tables(self) -> bool:
        """Test that all language files have correct navigation tables."""
        logger.info("🌐 Testing Language Navigation Tables")
        
        navigation_results = []
        
        for filename, info in self.expected_languages.items():
            file_path = self.project_root / filename
            
            if not file_path.exists():
                continue
                
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # Check for language navigation table
                has_navigation = "多语言文档" in content or "多言語ドキュメント" in content or "Multi-Language Documentation" in content or "多語言文檔" in content
                
                # Check for all language links
                language_links_found = []
                language_links_missing = []
                
                for other_filename, other_info in self.expected_languages.items():
                    link_pattern = f"[{other_filename}]"
                    if link_pattern in content:
                        language_links_found.append(other_filename)
                    else:
                        language_links_missing.append(other_filename)
                
                file_result = {
                    "file": filename,
                    "has_navigation": has_navigation,
                    "links_found": len(language_links_found),
                    "links_missing": len(language_links_missing),
                    "success": has_navigation and len(language_links_missing) == 0
                }
                
                navigation_results.append(file_result)
                
                if file_result["success"]:
                    logger.info(f"✅ {filename}: Navigation complete")
                else:
                    logger.error(f"❌ {filename}: Navigation incomplete")
                    if not has_navigation:
                        logger.error(f"   Missing navigation section")
                    if language_links_missing:
                        logger.error(f"   Missing links: {language_links_missing}")
                
            except Exception as e:
                logger.error(f"❌ Error reading {filename}: {e}")
                navigation_results.append({
                    "file": filename,
                    "success": False,
                    "error": str(e)
                })
        
        overall_success = all(result["success"] for result in navigation_results)
        
        result = {
            "test": "Language Navigation Tables",
            "files_tested": len(navigation_results),
            "success": overall_success,
            "results": navigation_results
        }
        
        self.test_results.append(result)
        return overall_success
    
    def test_content_structure_consistency(self) -> bool:
        """Test that all language files have consistent content structure."""
        logger.info("📋 Testing Content Structure Consistency")
        
        # Key sections that should exist in all language versions
        expected_sections = [
            "核心功能|Core Features|コア機能",  # Core Features
            "快速开始|Quick Start|クイックスタート|快速開始",  # Quick Start
            "API使用|API Usage|API使用方法",  # API Usage
            "安装|Installation|インストール|安裝",  # Installation
            "配置|Configuration|設定",  # Configuration
            "安全|Security|セキュリティ",  # Security
            "贡献|Contributing|コントリビューション|貢獻",  # Contributing
            "许可证|License|ライセンス|許可證"  # License
        ]
        
        structure_results = []
        
        for filename, info in self.expected_languages.items():
            file_path = self.project_root / filename
            
            if not file_path.exists():
                continue
                
            try:
                content = file_path.read_text(encoding='utf-8')
                
                sections_found = []
                sections_missing = []
                
                for section_pattern in expected_sections:
                    # Use regex to find section headers
                    pattern = rf"##.*?({section_pattern})"
                    if re.search(pattern, content, re.IGNORECASE):
                        sections_found.append(section_pattern.split('|')[0])
                    else:
                        sections_missing.append(section_pattern.split('|')[0])
                
                # Check for basic content requirements
                has_title = content.startswith('#')
                has_badges = '[![' in content
                has_code_examples = '```' in content
                
                file_result = {
                    "file": filename,
                    "has_title": has_title,
                    "has_badges": has_badges,
                    "has_code_examples": has_code_examples,
                    "sections_found": len(sections_found),
                    "sections_missing": len(sections_missing),
                    "success": has_title and has_badges and has_code_examples and len(sections_missing) <= 2  # Allow some flexibility
                }
                
                structure_results.append(file_result)
                
                if file_result["success"]:
                    logger.info(f"✅ {filename}: Structure consistent")
                else:
                    logger.error(f"❌ {filename}: Structure issues")
                    if not has_title:
                        logger.error(f"   Missing title")
                    if not has_badges:
                        logger.error(f"   Missing badges")
                    if not has_code_examples:
                        logger.error(f"   Missing code examples")
                    if sections_missing:
                        logger.error(f"   Missing sections: {sections_missing[:3]}")  # Show first 3
                
            except Exception as e:
                logger.error(f"❌ Error analyzing {filename}: {e}")
                structure_results.append({
                    "file": filename,
                    "success": False,
                    "error": str(e)
                })
        
        overall_success = all(result["success"] for result in structure_results)
        
        result = {
            "test": "Content Structure Consistency",
            "files_tested": len(structure_results),
            "success": overall_success,
            "results": structure_results
        }
        
        self.test_results.append(result)
        return overall_success
    
    def test_language_specific_content(self) -> bool:
        """Test that language-specific content is appropriate."""
        logger.info("🌍 Testing Language-Specific Content")
        
        language_content_tests = {
            "README.md": {
                "expected_patterns": ["English", "Enterprise", "Multi-Language Documentation"],
                "forbidden_patterns": ["中文", "日本語", "한국어"]
            },
            "README.zh-CN.md": {
                "expected_patterns": ["简体中文", "企业级", "多语言文档"],
                "forbidden_patterns": ["Traditional Chinese", "繁體"]
            },
            "README.zh-HK.md": {
                "expected_patterns": ["繁體中文", "企業級", "多語言文檔"],
                "forbidden_patterns": ["简体中文", "簡體"]
            },
            "README.ja.md": {
                "expected_patterns": ["日本語", "エンタープライズ", "多言語ドキュメント"],
                "forbidden_patterns": ["中文", "Korean"]
            }
        }
        
        language_results = []
        
        for filename, tests in language_content_tests.items():
            file_path = self.project_root / filename
            
            if not file_path.exists():
                continue
                
            try:
                content = file_path.read_text(encoding='utf-8')
                
                expected_found = []
                expected_missing = []
                forbidden_found = []
                
                # Check expected patterns
                for pattern in tests["expected_patterns"]:
                    if pattern in content:
                        expected_found.append(pattern)
                    else:
                        expected_missing.append(pattern)
                
                # Check forbidden patterns
                for pattern in tests["forbidden_patterns"]:
                    if pattern in content:
                        forbidden_found.append(pattern)
                
                file_result = {
                    "file": filename,
                    "expected_found": len(expected_found),
                    "expected_missing": len(expected_missing),
                    "forbidden_found": len(forbidden_found),
                    "success": len(expected_missing) <= 1 and len(forbidden_found) == 0  # Allow some flexibility
                }
                
                language_results.append(file_result)
                
                if file_result["success"]:
                    logger.info(f"✅ {filename}: Language content appropriate")
                else:
                    logger.error(f"❌ {filename}: Language content issues")
                    if expected_missing:
                        logger.error(f"   Missing expected: {expected_missing}")
                    if forbidden_found:
                        logger.error(f"   Contains forbidden: {forbidden_found}")
                
            except Exception as e:
                logger.error(f"❌ Error checking language content in {filename}: {e}")
                language_results.append({
                    "file": filename,
                    "success": False,
                    "error": str(e)
                })
        
        overall_success = all(result["success"] for result in language_results)
        
        result = {
            "test": "Language-Specific Content",
            "files_tested": len(language_results),
            "success": overall_success,
            "results": language_results
        }
        
        self.test_results.append(result)
        return overall_success
    
    def test_file_sizes_reasonable(self) -> bool:
        """Test that all language files have reasonable sizes."""
        logger.info("📏 Testing File Sizes")
        
        size_results = []
        sizes = []
        
        for filename, info in self.expected_languages.items():
            file_path = self.project_root / filename
            
            if not file_path.exists():
                continue
                
            try:
                file_size = file_path.stat().st_size
                sizes.append(file_size)
                
                # Reasonable size: between 10KB and 200KB
                is_reasonable = 10000 <= file_size <= 200000
                
                file_result = {
                    "file": filename,
                    "size_bytes": file_size,
                    "size_kb": round(file_size / 1024, 1),
                    "reasonable": is_reasonable
                }
                
                size_results.append(file_result)
                
                if is_reasonable:
                    logger.info(f"✅ {filename}: {file_result['size_kb']}KB (reasonable)")
                else:
                    logger.error(f"❌ {filename}: {file_result['size_kb']}KB (unreasonable)")
                
            except Exception as e:
                logger.error(f"❌ Error checking size of {filename}: {e}")
                size_results.append({
                    "file": filename,
                    "reasonable": False,
                    "error": str(e)
                })
        
        # Check size consistency (files shouldn't vary too much)
        if sizes:
            avg_size = sum(sizes) / len(sizes)
            size_consistency = all(0.5 * avg_size <= size <= 2.0 * avg_size for size in sizes)
        else:
            size_consistency = False
        
        overall_success = all(result["reasonable"] for result in size_results) and size_consistency
        
        result = {
            "test": "File Sizes",
            "files_tested": len(size_results),
            "average_size_kb": round(sum(sizes) / len(sizes) / 1024, 1) if sizes else 0,
            "size_consistency": size_consistency,
            "success": overall_success,
            "results": size_results
        }
        
        self.test_results.append(result)
        return overall_success
    
    def run_all_tests(self):
        """Run comprehensive multi-language documentation tests."""
        logger.info("🌐 Starting Multi-Language Documentation Test Suite")
        logger.info("=" * 70)
        
        # Run all tests
        test1_passed = self.test_file_existence()
        test2_passed = self.test_language_navigation_tables()
        test3_passed = self.test_content_structure_consistency()
        test4_passed = self.test_language_specific_content()
        test5_passed = self.test_file_sizes_reasonable()
        
        # Generate comprehensive report
        self.generate_test_report()
        
        return all([test1_passed, test2_passed, test3_passed, test4_passed, test5_passed])
    
    def generate_test_report(self):
        """Generate comprehensive test report."""
        logger.info("\n" + "=" * 70)
        logger.info("📊 Multi-Language Documentation Test Report")
        logger.info("=" * 70)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📈 Test Summary:")
        print(f"   Total Test Categories: {total_tests}")
        print(f"   Successful: {successful_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        # Show individual test results
        print(f"\n📋 Test Results:")
        for result in self.test_results:
            status_icon = "✅" if result["success"] else "❌"
            print(f"   {status_icon} {result['test']}")
            
            # Show additional details for failed tests
            if not result["success"]:
                if "missing" in result and result["missing"]:
                    print(f"     Missing: {result['missing'][:3]}...")  # Show first 3
                if "error" in result:
                    print(f"     Error: {result['error']}")
        
        # Language coverage summary
        existing_files = []
        for result in self.test_results:
            if result["test"] == "Language File Existence":
                existing_files = result.get("existing", [])
                break
        
        print(f"\n🌐 Language Coverage:")
        print(f"   Total Languages Supported: {len(existing_files)}")
        for filename in existing_files:
            if filename in self.expected_languages:
                info = self.expected_languages[filename]
                print(f"   {info['flag']} {info['lang']}: {filename}")
        
        # Content quality summary
        print(f"\n📚 Documentation Quality:")
        structure_test = next((r for r in self.test_results if r["test"] == "Content Structure Consistency"), None)
        if structure_test and structure_test["success"]:
            print("   ✅ Consistent structure across all languages")
        else:
            print("   ⚠️ Structure inconsistencies detected")
        
        navigation_test = next((r for r in self.test_results if r["test"] == "Language Navigation Tables"), None)
        if navigation_test and navigation_test["success"]:
            print("   ✅ Complete language navigation in all files")
        else:
            print("   ⚠️ Navigation issues detected")
        
        language_test = next((r for r in self.test_results if r["test"] == "Language-Specific Content"), None)
        if language_test and language_test["success"]:
            print("   ✅ Appropriate language-specific content")
        else:
            print("   ⚠️ Language content issues detected")
        
        # Deployment readiness
        print(f"\n🚀 Multi-Language Documentation Status:")
        if success_rate >= 90:
            print("   🎉 Excellent! Multi-language documentation is production-ready")
            print("   📈 All languages properly configured with complete navigation")
        elif success_rate >= 70:
            print("   ⚠️ Good progress, minor issues to address")
            print("   🔧 Review failed tests before full deployment")
        else:
            print("   🚨 Significant issues detected")
            print("   🛠️ Major improvements needed before deployment")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if len(existing_files) >= 4:
            print("   ✅ Good language coverage achieved")
        else:
            print("   📝 Consider adding more language versions")
        
        if success_rate >= 80:
            print("   🌟 Ready for international users")
        else:
            print("   🔧 Fix navigation and content issues first")
        
        print("\n" + "=" * 70)
        print("✨ Multi-Language Documentation Test Complete")
        print("=" * 70)


def main():
    """Main test execution function."""
    print("🌐 Enterprise Media Content Management Platform")
    print("🔍 Multi-Language Documentation Test Suite")
    print("=" * 70)
    
    try:
        # Get project root directory
        project_root = Path(__file__).parent.parent
        
        tester = MultiLanguageDocumentationTester(str(project_root))
        success = tester.run_all_tests()
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
