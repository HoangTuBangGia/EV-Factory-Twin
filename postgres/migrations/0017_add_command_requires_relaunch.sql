-- Preserve an approved scenario when the connected ROS topology needs a relaunch.

alter type public.command_status add value if not exists 'REQUIRES_RELAUNCH' after 'COMPLETED';
