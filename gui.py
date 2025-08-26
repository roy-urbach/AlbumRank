import tkinter as tk
from tkinter import ttk, messagebox
import requests
from PIL import ImageTk, Image
from io import BytesIO
from enum import Enum

from classes import Artist


class MusicRankingApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Music Ranking Application")
        self.geometry("800x770")

        self.artist = None
        self.current_album = None

        self.create_widgets()

    def create_widgets(self):
        self.container = ttk.Frame(self)
        self.container.pack(fill=tk.BOTH, expand=True)

        self.frames = {}
        for P in Pages:
            frame = P.value(parent=self.container, controller=self)
            self.frames[P] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(Pages.ArtistSelection)

    def show_frame(self, page):
        frame = self.frames[page]
        frame.tkraise()

    def select_artist(self, artist_name):
        try:
            # PATH for saving data - adjust as needed for a standalone app
            # For a standalone app, you might use a directory relative to the script or user's home
            self.artist = Artist(name=artist_name)
            self.show_album_list()
        except ValueError as e:
            messagebox.showerror("Artist Not Found", str(e))
        # except Exception as e:
        #     messagebox.showerror("Error", f"An error occurred while fetching artist data: {e}")

    def show_album_list(self):
        album_list_frame = self.frames[Pages.AlbumList]
        album_list_frame.load_albums(self.artist.albums)
        self.show_frame(Pages.AlbumList)

    def rank_album(self, album):
        self.current_album = album
        album_ranking_frame = self.frames[Pages.AlbumRank]
        album_ranking_frame.load_album(album)
        self.show_frame(Pages.AlbumRank)

    def album_ranking_complete(self):
        self.artist.save_rankings() # Save after ranking an album
        self.show_album_list() # Return to album list

    def show_ranking(self):
        show_ranking_frame = self.frames[Pages.ShowRank]
        show_ranking_frame.load_ranking(self.artist.sorted_albums())
        self.show_frame(Pages.ShowRank)

    def go_back_to_menu(self):
        self.show_frame(Pages.AlbumList) # Assuming album list is the main menu after artist selection

    def return_to_artist(self):
        self.show_frame(Pages.ArtistSelection)


class ArtistSelectionPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.label = ttk.Label(self, text="Enter Artist Name:")
        self.label.pack(pady=10)

        self.artist_name_entry = ttk.Entry(self, width=40)
        self.artist_name_entry.pack(pady=5)

        self.search_button = ttk.Button(self, text="Search and Select Artist", command=self.search_and_select)
        self.search_button.pack(pady=10)

    def search_and_select(self):
        artist_name = self.artist_name_entry.get()
        if artist_name:
            self.controller.select_artist(artist_name)
        else:
            messagebox.showwarning("Input Error", "Please enter an artist name.")


class AlbumListPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.label = ttk.Label(self, text="Select an Album to Rank:")
        self.label.pack(pady=10)

        self.album_listbox = tk.Listbox(self, width=50, height=15)
        self.album_listbox.pack(pady=5)
        self.album_listbox.bind('<<ListboxSelect>>', self.on_album_select)

        self.rank_button = ttk.Button(self, text="Rank Selected Album", command=self.rank_selected_album, state=tk.DISABLED)
        self.rank_button.pack(pady=5)

        self.show_ranking_button = ttk.Button(self, text="Show Artist Ranking", command=self.controller.show_ranking)
        self.show_ranking_button.pack(pady=5)

        self.show_ranking_button = ttk.Button(self, text="Return to artist choosing", command=self.controller.return_to_artist)
        self.show_ranking_button.pack(pady=5)

        self.albums = [] # To store album objects

    def load_albums(self, albums):
        self.albums = albums
        self.album_listbox.delete(0, tk.END)
        for album in self.albums:
            score_str = f" ({album.get_final_score():.2f})" if album.get_final_score() is not None else ""
            self.album_listbox.insert(tk.END, f"{album.name} - {album.release_year}{score_str}")
        self.rank_button.config(state=tk.DISABLED) # Disable button until an album is selected

    def on_album_select(self, event):
        if self.album_listbox.curselection():
            self.rank_button.config(state=tk.NORMAL)
        else:
            self.rank_button.config(state=tk.DISABLED)

    def rank_selected_album(self):
        selected_index = self.album_listbox.curselection()
        if selected_index:
            album_index = selected_index[0]
            selected_album = self.albums[album_index]
            self.controller.rank_album(selected_album)


class AlbumRankingPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.album = None
        self.current_song = None
        # self.preview_audio = None # To hold the loaded audio data

        self.album_name_label = ttk.Label(self, text="")
        self.album_name_label.pack(pady=10)

        self.cover_label = ttk.Label(self)
        self.cover_label.pack(pady=5)

        self.experience_label = ttk.Label(self, text="Cohesive Experience:")
        self.experience_label.pack()
        self.experience_slider = ttk.Scale(self, from_=0, to=10, orient=tk.HORIZONTAL, length=300)
        self.experience_slider.pack()

        self.replay_label = ttk.Label(self, text="Replay Value:")
        self.replay_label.pack()
        self.replay_slider = ttk.Scale(self, from_=0, to=10, orient=tk.HORIZONTAL, length=300)
        self.replay_slider.pack()

        self.song_label = ttk.Label(self, text="Select a Song to Rank:")
        self.song_label.pack(pady=10)

        self.song_listbox = tk.Listbox(self, width=50, height=10)
        self.song_listbox.pack(pady=5)
        self.song_listbox.bind('<<ListboxSelect>>', self.on_song_select)

        self.song_rank_label = ttk.Label(self, text="Song Rank:")
        self.song_rank_label.pack()
        self.song_rank_slider = ttk.Scale(self, from_=0, to=10, orient=tk.HORIZONTAL, length=300)
        self.song_rank_slider.pack()
        self.song_rank_slider.bind("<ButtonRelease-1>", self.on_rank_slider_release) # Save rank when slider is released

        # self.preview_button = ttk.Button(self, text="Play Preview", command=self.play_preview, state=tk.DISABLED)
        # self.preview_button.pack(pady=5)

        self.ranking_summary_label = ttk.Label(self, text="Ranking Summary:")
        self.ranking_summary_label.pack(pady=10)

        self.ranking_text = tk.Text(self, width=60, height=8, state=tk.DISABLED)
        self.ranking_text.pack(pady=5)

        self.back_button = ttk.Button(self, text="Back to Albums", command=self.controller.album_ranking_complete)
        self.back_button.pack(pady=10)

    def load_album(self, album):
        self.album = album
        self.album_name_label.config(text=f"{album.name} - {album.release_year}")

        # Load and display album cover
        self.load_album_cover()

        # Set initial slider values
        self.experience_slider.set(self.album.e_value if self.album.e_value is not None else 5.0)
        self.replay_slider.set(self.album.r_value if self.album.r_value is not None else 5.0)

        # Bind slider changes to update album values and save
        self.experience_slider.bind("<ButtonRelease-1>", self.on_album_slider_release)
        self.replay_slider.bind("<ButtonRelease-1>", self.on_album_slider_release)

        # Load songs into listbox
        self.song_listbox.delete(0, tk.END)
        self.album.fetch_songs()
        if self.album.songs:
            for song in self.album.songs:
                rank_str = f" ({song.rank_value:.1f})" if song.rank_value is not None else ""
                self.song_listbox.insert(tk.END, f"{song.name}{rank_str}")
        self.on_song_select(None) # Trigger initial song selection state

        self.update_ranking_summary()

    def load_album_cover(self):
        if self.album and self.album.cover_url:
            try:
                response = requests.get(self.album.cover_url, stream=True)
                response.raise_for_status()
                image_data = response.content
                img = Image.open(BytesIO(image_data))
                img = img.resize((150, 150), Image.LANCZOS)
                self.album_cover_photo = ImageTk.PhotoImage(img)
                self.cover_label.config(image=self.album_cover_photo)
            except Exception as e:
                print(f"Error loading album cover: {e}")
                self.cover_label.config(image="") # Clear image on error
        else:
            self.cover_label.config(image="") # Clear image if no cover URL

    def on_album_slider_release(self, event):
        """Update album e and r values when sliders are released."""
        if self.album:
            self.album.set_e_r(self.experience_slider.get(), self.replay_slider.get())
            self.update_ranking_summary()
            self.controller.artist.save_rankings()

    def on_song_select(self, event):
        selected_index = self.song_listbox.curselection()
        if selected_index and self.album and self.album.songs:
            song_index = selected_index[0]
            self.current_song = self.album.songs[song_index]
            # Set song rank slider value
            self.song_rank_slider.set(self.current_song.rank_value if self.current_song.rank_value is not None else 5.0)
            # self.preview_button.config(state=tk.NORMAL)

            # # Stop any currently playing preview
            # if self.preview_audio:
            #      self.preview_audio.stop()
            #      self.preview_audio = None

        else:
            self.current_song = None
            self.song_rank_slider.set(5.0)
            # self.preview_button.config(state=tk.DISABLED)

    def on_rank_slider_release(self, event):
        """Update song rank when the slider is released."""
        if self.current_song:
            rank_value = round(self.song_rank_slider.get(), 1) # Round to one decimal place
            self.current_song.set_rank(rank_value)
            self.update_song_listbox() # Update song listbox to show new rank
            self.update_ranking_summary()
            self.controller.artist.save_rankings()

    def update_song_listbox(self):
        """Update the song listbox to reflect current song ranks."""
        if self.album and self.album.songs:
            selected_index = self.song_listbox.curselection() # Preserve selection
            self.song_listbox.delete(0, tk.END)
            for song in self.album.songs:
                rank_str = f" ({song.rank_value:.1f})" if song.rank_value is not None else ""
                self.song_listbox.insert(tk.END, f"{song.name}{rank_str}")
            if selected_index: # Restore selection
                 self.song_listbox.selection_set(selected_index[0])

    # preview_url was removed from the spotify API, sadly :(

    # def play_preview(self):
    #     if self.current_song:
    #         self.current_song.fetch_song_details()
    #     print(self.current_song, self.current_song.preview_url)
    #     if self.current_song and self.current_song.preview_url:
    #         try:
    #             # Use a simple audio player if available, or recommend one.
    #             # Tkinter itself doesn't have built-in audio playback.
    #             # For a real application, you'd integrate a library like pyglet, simpleaudio, or pygame.mixer.
    #             # This is a placeholder.
    #             print(f"Playing preview for: {self.current_song.name}")
    #             print(f"Preview URL: {self.current_song.preview_url}")
    #
    #             # Example using simpleaudio (requires installation: pip install simpleaudio)
    #             try:
    #                 import simpleaudio as sa
    #                 response = requests.get(self.current_song.preview_url, stream=True)
    #                 response.raise_for_status()
    #                 audio_data = response.content
    #                 # simpleaudio might have issues with direct byte playback of mp3.
    #                 # A common workaround is to save to a temp file first.
    #                 temp_file = "temp_preview.mp3"
    #                 with open(temp_file, "wb") as f:
    #                      f.write(audio_data)
    #                 self.preview_audio = sa.WaveObject.from_wave_file(temp_file) # Assumes wave format is compatible
    #                 play_obj = self.preview_audio.play()
    #                 # You might want to manage the play_obj to stop playback later
    #             except ImportError:
    #                  messagebox.showinfo("Playback Info", "Install 'simpleaudio' for preview playback.")
    #             except Exception as e:
    #                  print(f"Error playing preview: {e}")
    #                  messagebox.showerror("Playback Error", f"Could not play preview: {e}")
    #
    #         except Exception as e:
    #             print(f"Error getting preview URL: {e}")
    #     else:
    #         messagebox.showinfo("No Preview", "No preview available for this song.")

    def update_ranking_summary(self):
        """Update the text widget with the current ranking summary."""
        if self.album:
            df = self.album.show_rank()
            self.ranking_text.config(state=tk.NORMAL)
            self.ranking_text.delete(1.0, tk.END)
            self.ranking_text.insert(tk.END, df.to_string(index=False, float_format=lambda f: f"{f:.1f}"))
            self.ranking_text.config(state=tk.DISABLED)


class ShowRankingPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.label = ttk.Label(self, text="Artist Ranking:")
        self.label.pack(pady=10)

        self.ranking_text = tk.Text(self, width=80, height=20, state=tk.DISABLED)
        self.ranking_text.pack(pady=5)

        self.back_button = ttk.Button(self, text="Back to Albums", command=self.controller.go_back_to_menu)
        self.back_button.pack(pady=10)

    def load_ranking(self, ranking_df):
        self.ranking_text.config(state=tk.NORMAL)
        self.ranking_text.delete(1.0, tk.END)
        if not ranking_df.empty:
            self.ranking_text.insert(tk.END, ranking_df.to_string(index=False, float_format=lambda f: f"{f:.2f}"))
        else:
            self.ranking_text.insert(tk.END, "No albums have been ranked yet.")
        self.ranking_text.config(state=tk.DISABLED)


class Pages(Enum):
    ArtistSelection = ArtistSelectionPage
    AlbumList = AlbumListPage
    AlbumRank = AlbumRankingPage
    ShowRank = ShowRankingPage