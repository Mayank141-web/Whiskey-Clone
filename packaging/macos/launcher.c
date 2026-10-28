/* Beer.app launcher: starts the bundled Python (native arm64 or x86_64) running Beer's GUI. */
#include <libgen.h>
#include <limits.h>
#include <mach-o/dyld.h>
#include <spawn.h>
#include <sys/wait.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

extern char **environ;

/* Clear the download quarantine flag from the whole app once the user has opened it,
   so macOS doesn't block the Python inside it. Fails harmlessly on read-only disk images. */
static void unquarantine(const char *bundle) {
    pid_t pid;
    char *args[] = {"/usr/bin/xattr", "-dr", "com.apple.quarantine", (char *)bundle, NULL};
    if (posix_spawn(&pid, args[0], NULL, NULL, args, environ) == 0) {
        int status;
        waitpid(pid, &status, 0);
    }
}

int main(int argc, char **argv) {
    char exe[PATH_MAX], real[PATH_MAX], contents[PATH_MAX], tmp[PATH_MAX], bundle[PATH_MAX];
    char python[PATH_MAX], lib[PATH_MAX], path[PATH_MAX * 2];
    uint32_t size = sizeof(exe);
    if (_NSGetExecutablePath(exe, &size) != 0 || !realpath(exe, real)) {
        fprintf(stderr, "Beer: cannot locate itself\n");
        return 1;
    }
    /* real = .../Beer.app/Contents/MacOS/Beer */
    snprintf(tmp, sizeof(tmp), "%s", real);
    snprintf(contents, sizeof(contents), "%s", dirname(tmp));      /* .../Contents/MacOS */
    snprintf(tmp, sizeof(tmp), "%s", contents);
    snprintf(contents, sizeof(contents), "%s", dirname(tmp));      /* .../Contents */
    snprintf(tmp, sizeof(tmp), "%s", contents);
    snprintf(bundle, sizeof(bundle), "%s", dirname(tmp));          /* .../Beer.app */
#if defined(__arm64__) || defined(__aarch64__)
    snprintf(python, sizeof(python), "%s/Resources/python-arm64/bin/python3", contents);
#else
    snprintf(python, sizeof(python), "%s/Resources/python-x86_64/bin/python3", contents);
#endif
    snprintf(lib, sizeof(lib), "%s/Resources/lib", contents);
    const char *old_path = getenv("PATH");
    snprintf(path, sizeof(path), "/opt/homebrew/bin:/usr/local/bin:%s",
             old_path ? old_path : "/usr/bin:/bin:/usr/sbin:/sbin");
    setenv("PATH", path, 1);
    setenv("PYTHONPATH", lib, 1);
    setenv("PYTHONDONTWRITEBYTECODE", "1", 1);
    setenv("BEER_APP_BUNDLE", bundle, 1);
    unquarantine(bundle);
    unsetenv("PYTHONHOME");

    /* "Beer --cli <args>" runs the command line instead of the window (used by tests). */
    int cli = argc > 1 && strcmp(argv[1], "--cli") == 0;
    char **args = calloc((size_t)argc + 5, sizeof(char *));
    int n = 0;
    args[n++] = python;
    args[n++] = "-m";
    args[n++] = "beer";
    if (!cli) args[n++] = "gui";
    for (int i = cli ? 2 : 1; i < argc; i++) {
        if (strncmp(argv[i], "-psn_", 5) == 0) continue; /* old Finder process serial number */
        args[n++] = argv[i];
    }
    args[n] = NULL;
    execv(python, args);
    perror("Beer: could not start Python");
    return 1;
}
