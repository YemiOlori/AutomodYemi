from rich.table import Table
from rich.console import Console
from rich import box

from automod.automod import AutoModClient
from automod.automod import TrenchesAutoModClient
# from automod.audio import AudioClient as Audio


class AutoMod(AutoModClient):
    def __init__(self):
        super().__init__()

    def get_hallway(self, max_limit=30):

        # Get channels and print
        console = Console(width=180)
        table = Table(show_header=True, header_style="bold magenta", box=box.MINIMAL_HEAVY_HEAD, leading=True)
        table.add_column("speakers", width=8, justify='center')
        table.add_column("users", width=8, justify='center')
        table.add_column("type", width=8)
        table.add_column("channel", width=10)
        table.add_column("club", width=35, no_wrap=True)
        table.add_column("title", style="cyan", width=70)

        feed = self.client.feed()
        channel_list = [item for item in feed['items'] if 'channel' in item.keys()]

        for index, channel in enumerate(channel_list):
            channel = channel['channel']
            if index > max_limit:
                break
            
            type_ = "social" if channel.get("is_social_mode") else "private" if channel.get("is_private") else ""
            club = channel.get("club").get("name") if channel.get("club") else ""

            table.add_row(
                str(int(channel.get("num_speakers"))),
                str(int(channel.get("num_all"))),
                str(type_),
                str(channel.get("channel")),
                str(club),
                str(channel.get("topic")),
            )

        console.print(table)

        return
        
    def automod_cli(self, channel, api_retry_interval_sec=10, thread_timeout=120,
                    announcement=None, announcement_interval_min=60, announcement_delay=0, audio=True):
        init = self.automod_init(channel, api_retry_interval_sec, thread_timeout,
                                 announcement, announcement_interval_min, announcement_delay)

        if audio:
            self.start_audio(channel, join_info=init)
            self.unmute_audio()


class TrenchesAutoMod(TrenchesAutoModClient):
    def __init__(self, account, config):
        super().__init__(account, config)
    
    def get_hallway(self, max_limit=30):
        
        # Get channels and print
        console = Console(width=180)
        table = Table(show_header=True, header_style="bold magenta", box=box.MINIMAL_HEAVY_HEAD, leading=True)
        table.add_column("speakers", width=8, justify='center')
        table.add_column("users", width=8, justify='center')
        table.add_column("type", width=8)
        table.add_column("channel", width=10)
        table.add_column("club", width=35, no_wrap=True)
        table.add_column("title", style="cyan", width=70)
        
        feed = self.client.feed()
        channel_list = [item for item in feed['items'] if 'channel' in item.keys()]
        
        for index, channel in enumerate(channel_list):
            channel = channel['channel']
            if index > max_limit:
                break
            
            type_ = "social" if channel.get("is_social_mode") else "private" if channel.get("is_private") else ""
            club = channel.get("club").get("name") if channel.get("club") else ""
            
            table.add_row(
                str(int(channel.get("num_speakers"))),
                str(int(channel.get("num_all"))),
                str(type_),
                str(channel.get("channel")),
                str(club),
                str(channel.get("topic")),
            )
        
        console.print(table)
        
        return
    
    def automod_cli(self, channel, api_retry_interval_sec=10, thread_timeout=120,
                    announcement=None, announcement_interval_min=60, announcement_delay=0, audio=True):
        init = self.automod_init(channel, api_retry_interval_sec, thread_timeout,
                                 announcement, announcement_interval_min, announcement_delay)
        
        if audio:
            self.start_audio(channel, join_info=init)
            self.unmute_audio()