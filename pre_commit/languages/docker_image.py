from __future__ import annotations

from collections.abc import Sequence

from pre_commit import lang_base
from pre_commit.languages.docker import docker_cmd
from pre_commit.prefix import Prefix

ENVIRONMENT_DIR = None
get_default_version = lang_base.basic_get_default_version
health_check = lang_base.basic_health_check
install_environment = lang_base.no_install
in_env = lang_base.no_env


def run_hook(
        prefix: Prefix,
        entry: str,
        args: Sequence[str],
        file_args: Sequence[str],
        *,
        is_local: bool,
        require_serial: bool,
        color: bool,
) -> tuple[int, bytes]:  # pragma: win32 no cover
    cmd = lang_base.hook_cmd(entry, args)

    # To prevent duplicate simultaneous image pull attempts in `run_xargs`, we
    # opportunistically try to precache the Docker image by pulling it here.
    try:
        # Attempt to precache only if we can easily identify the image tag.
        #
        # Our public docs state that `entry` must be a Docker image tag with
        # optionally an entrypoint override, but there might be users who
        # instead treat `entry` as a place to put arbitrary `docker run` args.
        #
        # To accommodate such users who are relying on undocumented behavior,
        # we check whether the first non-entrypoint argument is another option,
        # i.e. it begins with a dash. If not, it must be the image name
        # according to `docker run --help`:
        #
        #   docker run [OPTIONS] IMAGE [COMMAND] [ARG...]`
        if cmd[0] == '--entrypoint':
            first_non_ep_arg = cmd[2]
        elif cmd[0].startswith('--entrypoint='):
            first_non_ep_arg = cmd[1]
        else:
            first_non_ep_arg = cmd[0]
        if not first_non_ep_arg.startswith('-'):
            # We've found the image tag
            lang_base.setup_cmd(prefix, ('docker', 'pull', first_non_ep_arg))
    except Exception:
        # We swallow the error because this precaching pull is a nonessential
        # speed optimization. If it fails, `docker run` (possibly multiple
        # invocations of it, redundantly) will still try to pull the image
        # later as needed.
        pass

    return lang_base.run_xargs(
        docker_cmd(color=color) + cmd,
        file_args,
        require_serial=require_serial,
        color=color,
    )
