import subprocess
import time
import datetime
import sys

def run_git_command(cmd):
    """Execute a git command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            cwd='.',
            capture_output=True,
            text=True,
            check=False  # Don't raise exception on non-zero exit
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        print(f"Error running command {' '.join(cmd)}: {e}", file=sys.stderr)
        return -1, '', str(e)

def has_changes():
    """Check if there are any changes to commit (staged or unstaged)."""
    _, stdout, _ = run_git_command(['git', 'status', '--porcelain'])
    return bool(stdout.strip())

def main():
    print("Starting automated Git sync every 5 seconds...")
    while True:
        try:
            if has_changes():
                print(f"{datetime.datetime.now().isoformat()}: Changes detected. Committing and pushing...")
                
                # Stage all changes
                ret_code, _, stderr = run_git_command(['git', 'add', '.'])
                if ret_code != 0:
                    print(f"Failed to stage changes: {stderr}", file=sys.stderr)
                    time.sleep(5)
                    continue
                
                # Commit
                commit_msg = f"Auto-commit at {datetime.datetime.now().isoformat()}"
                ret_code, _, stderr = run_git_command(['git', 'commit', '-m', commit_msg])
                if ret_code == 0:
                    print(f"Committed: {commit_msg}")
                    # Push
                    ret_code, stdout, stderr = run_git_command(['git', 'push', '-u', 'origin', 'main'])
                    if ret_code == 0:
                        print(f"Pushed successfully.")
                    else:
                        print(f"Push failed: {stderr}", file=sys.stderr)
                elif "nothing to commit" in stderr.lower():
                    print("No changes to commit after staging.")
                else:
                    print(f"Commit failed: {stderr}", file=sys.stderr)
            else:
                print(f"{datetime.datetime.now().isoformat()}: No changes. Waiting...")
            
            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\nStopping automated sync.")
            break
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            time.sleep(5)

if __name__ == '__main__':
    main()