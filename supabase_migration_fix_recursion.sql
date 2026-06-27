-- ============================================================
-- Fix: infinite recursion in RLS policies (ponds <-> pond_members)
-- Chạy sau migration trước, 1 lần trong Supabase SQL Editor
-- ============================================================

-- Helper functions chạy với quyền cao hơn để cắt vòng lặp RLS
create or replace function public.is_pond_owner(p_pond_id uuid)
returns boolean
language sql security definer set search_path = public stable
as $$
  select exists (select 1 from public.ponds where id = p_pond_id and owner_id = auth.uid());
$$;

create or replace function public.is_pond_member(p_pond_id uuid)
returns boolean
language sql security definer set search_path = public stable
as $$
  select exists (select 1 from public.pond_members where pond_id = p_pond_id and user_id = auth.uid());
$$;

-- Cập nhật lại policies cho ponds dùng hàm trên (không subquery trực tiếp pond_members)
drop policy if exists "ponds_select" on public.ponds;
create policy "ponds_select" on public.ponds for select
  using (owner_id = auth.uid() or public.is_pond_member(id));

drop policy if exists "ponds_update" on public.ponds;
create policy "ponds_update" on public.ponds for update
  using (owner_id = auth.uid() or public.is_pond_member(id));

-- Policies cho measurements dùng hàm trên
drop policy if exists "measurements_select" on public.measurements;
create policy "measurements_select" on public.measurements for select
  using (public.is_pond_owner(pond_id) or public.is_pond_member(pond_id));

drop policy if exists "measurements_insert" on public.measurements;
create policy "measurements_insert" on public.measurements for insert
  with check (public.is_pond_owner(pond_id) or public.is_pond_member(pond_id));

-- Policies cho pond_members dùng hàm trên (không subquery trực tiếp ponds)
drop policy if exists "members_select" on public.pond_members;
create policy "members_select" on public.pond_members for select
  using (user_id = auth.uid() or public.is_pond_owner(pond_id));

drop policy if exists "members_delete" on public.pond_members;
create policy "members_delete" on public.pond_members for delete
  using (public.is_pond_owner(pond_id));
