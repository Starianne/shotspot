create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text not null unique check (username ~ '^[A-Za-z0-9_]{3,30}$'),
  display_name text,
  avatar_url text,
  bio text check (char_length(bio) <= 500),
  created_at timestamptz not null default timezone('utc', now())
);

create table public.posts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete restrict,
  image_url text not null,
  caption text,
  place_name text not null check (char_length(place_name) between 1 and 200),
  latitude double precision not null check (latitude between -90 and 90),
  longitude double precision not null check (longitude between -180 and 180),
  instagram_url text,
  created_at timestamptz not null default timezone('utc', now())
);

create index posts_created_at_idx on public.posts (created_at desc);
create index posts_user_id_created_at_idx on public.posts (user_id, created_at desc);

alter table public.profiles enable row level security;
alter table public.posts enable row level security;

create policy "Public profiles are readable"
  on public.profiles for select using (true);
create policy "Users can create their own profile"
  on public.profiles for insert with check (auth.uid() = id);
create policy "Users can update their own profile"
  on public.profiles for update using (auth.uid() = id) with check (auth.uid() = id);

create policy "Posts are publicly readable"
  on public.posts for select using (true);
create policy "Users can create their own posts"
  on public.posts for insert with check (auth.uid() = user_id);
create policy "Users can update their own posts"
  on public.posts for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users can delete their own posts"
  on public.posts for delete using (auth.uid() = user_id);

-- Create a public bucket named "photos" in Storage before applying these policies.
create policy "Public photo objects are readable"
  on storage.objects for select using (bucket_id = 'photos');
create policy "Users upload within their own folder"
  on storage.objects for insert to authenticated
  with check (bucket_id = 'photos' and (storage.foldername(name))[1] = (select auth.uid()::text));
create policy "Users delete within their own folder"
  on storage.objects for delete to authenticated
  using (bucket_id = 'photos' and (storage.foldername(name))[1] = (select auth.uid()::text));
