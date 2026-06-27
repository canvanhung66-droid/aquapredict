-- ============================================================
-- Multi-tenant: mỗi ao thuộc 1 chủ, chủ ao mời thêm người quản lý
-- Chạy 1 lần trong Supabase SQL Editor (Project > SQL Editor > New query)
-- ============================================================

-- 1) Thêm cột owner_id vào bảng ponds
alter table public.ponds
  add column if not exists owner_id uuid references auth.users(id) default auth.uid();

-- 2) Bảng thành viên được chia sẻ quyền quản lý ao
create table if not exists public.pond_members (
  id uuid primary key default gen_random_uuid(),
  pond_id uuid not null references public.ponds(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (pond_id, user_id)
);

-- 3) Hàm mời người dùng theo email (chạy với quyền cao hơn để tra auth.users)
create or replace function public.invite_pond_member(p_pond_id uuid, p_email text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_owner uuid;
  v_user_id uuid;
begin
  select owner_id into v_owner from public.ponds where id = p_pond_id;
  if v_owner is null or v_owner <> auth.uid() then
    raise exception 'Chỉ chủ ao mới được mời thành viên';
  end if;

  select id into v_user_id from auth.users where email = p_email limit 1;
  if v_user_id is null then
    raise exception 'Không tìm thấy người dùng với email %. Yêu cầu họ tạo tài khoản trước.', p_email;
  end if;

  insert into public.pond_members (pond_id, user_id)
  values (p_pond_id, v_user_id)
  on conflict (pond_id, user_id) do nothing;
end;
$$;

-- 4) Bật RLS
alter table public.ponds enable row level security;
alter table public.measurements enable row level security;
alter table public.pond_members enable row level security;

-- 5) Policy cho ponds: chỉ chủ ao hoặc thành viên được xem/sửa
drop policy if exists "ponds_select" on public.ponds;
create policy "ponds_select" on public.ponds for select
  using (
    owner_id = auth.uid()
    or exists (select 1 from public.pond_members m where m.pond_id = ponds.id and m.user_id = auth.uid())
  );

drop policy if exists "ponds_insert" on public.ponds;
create policy "ponds_insert" on public.ponds for insert
  with check (owner_id = auth.uid());

drop policy if exists "ponds_update" on public.ponds;
create policy "ponds_update" on public.ponds for update
  using (
    owner_id = auth.uid()
    or exists (select 1 from public.pond_members m where m.pond_id = ponds.id and m.user_id = auth.uid())
  );

drop policy if exists "ponds_delete" on public.ponds;
create policy "ponds_delete" on public.ponds for delete
  using (owner_id = auth.uid());

-- 6) Policy cho measurements: theo quyền của ao liên quan
drop policy if exists "measurements_select" on public.measurements;
create policy "measurements_select" on public.measurements for select
  using (
    exists (
      select 1 from public.ponds p
      where p.id = measurements.pond_id
        and (p.owner_id = auth.uid()
             or exists (select 1 from public.pond_members m where m.pond_id = p.id and m.user_id = auth.uid()))
    )
  );

drop policy if exists "measurements_insert" on public.measurements;
create policy "measurements_insert" on public.measurements for insert
  with check (
    exists (
      select 1 from public.ponds p
      where p.id = measurements.pond_id
        and (p.owner_id = auth.uid()
             or exists (select 1 from public.pond_members m where m.pond_id = p.id and m.user_id = auth.uid()))
    )
  );

-- 7) Policy cho pond_members: chủ ao quản lý danh sách, thành viên xem được mình trong danh sách
drop policy if exists "members_select" on public.pond_members;
create policy "members_select" on public.pond_members for select
  using (
    user_id = auth.uid()
    or exists (select 1 from public.ponds p where p.id = pond_members.pond_id and p.owner_id = auth.uid())
  );

drop policy if exists "members_delete" on public.pond_members;
create policy "members_delete" on public.pond_members for delete
  using (
    exists (select 1 from public.ponds p where p.id = pond_members.pond_id and p.owner_id = auth.uid())
  );
