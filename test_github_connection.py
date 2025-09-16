#!/usr/bin/env python3
"""
Test script to verify GitHub API connection and repository access
"""

import requests
import json

def test_github_connection():
    """Test GitHub API connection and repository access"""
    
    print("🔍 Testing GitHub API Connection")
    print("=" * 40)
    
    # Test 1: Basic GitHub API connectivity
    print("1. Testing GitHub API connectivity...")
    try:
        response = requests.get("https://api.github.com", timeout=10)
        if response.status_code == 200:
            print("✅ GitHub API is accessible")
        else:
            print(f"❌ GitHub API returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ GitHub API connection failed: {e}")
        return False
    
    # Test 2: Check if repository exists
    print("\n2. Testing repository access...")
    repo_url = "https://api.github.com/repos/jdrevnyak/IdPass"
    try:
        response = requests.get(repo_url, timeout=10)
        if response.status_code == 200:
            print("✅ Repository 'jdrevnyak/IdPass' exists and is accessible")
            repo_data = response.json()
            print(f"   Repository name: {repo_data.get('name')}")
            print(f"   Repository visibility: {repo_data.get('visibility', 'public')}")
        elif response.status_code == 404:
            print("❌ Repository 'jdrevnyak/IdPass' not found")
            print("   Possible reasons:")
            print("   - Repository doesn't exist")
            print("   - Repository is private and requires authentication")
            print("   - Repository name is incorrect")
        else:
            print(f"❌ Repository access failed with status: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Repository access failed: {e}")
    
    # Test 3: Check for releases
    print("\n3. Testing releases access...")
    releases_url = "https://api.github.com/repos/jdrevnyak/IdPass/releases"
    try:
        response = requests.get(releases_url, timeout=10)
        if response.status_code == 200:
            releases = response.json()
            if releases:
                print(f"✅ Found {len(releases)} release(s)")
                for release in releases[:3]:  # Show first 3 releases
                    print(f"   - {release.get('tag_name')}: {release.get('name', 'No title')}")
            else:
                print("⚠️  Repository exists but has no releases")
                print("   You need to create a release to test updates")
        elif response.status_code == 404:
            print("❌ Repository not found - cannot check releases")
        else:
            print(f"❌ Releases access failed with status: {response.status_code}")
    except Exception as e:
        print(f"❌ Releases access failed: {e}")
    
    # Test 4: Check user repositories
    print("\n4. Checking your repositories...")
    user_repos_url = "https://api.github.com/users/jdrevnyak/repos"
    try:
        response = requests.get(user_repos_url, timeout=10)
        if response.status_code == 200:
            repos = response.json()
            if repos:
                print(f"✅ Found {len(repos)} repository(ies)")
                print("   Available repositories:")
                for repo in repos[:5]:  # Show first 5 repos
                    print(f"   - {repo.get('name')} ({repo.get('visibility', 'public')})")
            else:
                print("❌ No repositories found for user 'jdrevnyak'")
        else:
            print(f"❌ User repositories access failed: {response.status_code}")
    except Exception as e:
        print(f"❌ User repositories access failed: {e}")
    
    print("\n" + "=" * 40)
    print("📋 Summary and Recommendations:")
    print("=" * 40)
    print("1. If repository doesn't exist:")
    print("   - Create repository 'IdPass' on GitHub")
    print("   - Upload your code")
    print("   - Create a release (e.g., v1.0.1)")
    print()
    print("2. If repository is private:")
    print("   - Make it public, OR")
    print("   - Use GitHub token for authentication")
    print()
    print("3. If repository name is wrong:")
    print("   - Update the repository name in nfc_reader_gui.py")
    print("   - Change 'repo_name' parameter in UpdateManager")

if __name__ == "__main__":
    test_github_connection()
